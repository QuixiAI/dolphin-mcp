"""
Ollama provider implementation for Dolphin MCP.

This module provides integration with Ollama models for text generation and tool usage,
including proper formatting of tool calls and their arguments.
"""

import json
import logging
import sys
import traceback
import copy
from typing import Dict, List, Any, Optional, Union, Mapping, TypeVar, cast, Callable

# Third-party imports
import httpx
from pydantic import BaseModel, ValidationError
# Import Ollama types for response parsing
from ollama import ResponseError
from ollama._types import ChatResponse, Message

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('dolphin_mcp.providers.ollama')

# Constants
DEFAULT_API_HOST = "http://localhost:11434"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 1024
EMPTY_JSON_VALUES = ('', '{}')

# Type definitions
JsonDict = Dict[str, Any]
OllamaToolType = Dict[str, Any]
MessageType = Dict[str, Any]
T = TypeVar('T')

# Global mapping to track original tool names
tool_name_mapping: Dict[str, str] = {}


def sanitize_tool_name(name: str) -> str:
    """
    Sanitize tool name for compatibility with various systems.
    
    Args:
        name: The original tool name
        
    Returns:
        A sanitized version of the name with problematic characters replaced
    """
    return name.replace("-", "_").replace(" ", "_").lower()


def parse_json_safely(json_str: Union[str, Any]) -> JsonDict:
    """
    Parse a JSON string safely, handling edge cases and returning an empty dict for invalid inputs.
    
    Args:
        json_str: String containing JSON or any other value
        
    Returns:
        Parsed JSON dict or empty dict if parsing fails
    """
    # Handle non-string inputs
    if not isinstance(json_str, str):
        return {}
    
    # Handle empty inputs
    json_str = json_str.strip()
    if not json_str or json_str in EMPTY_JSON_VALUES:
        return {}
    
    # Attempt to parse
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse JSON string: {json_str}")
        return {}


def preprocess_messages(messages: List[MessageType]) -> List[MessageType]:
    """
    Preprocess conversation messages to ensure tool_calls.function.arguments are dictionaries.
    The Ollama server expects arguments as objects, not strings.
    
    Args:
        messages: List of message objects from the conversation history
        
    Returns:
        Processed copy of messages with tool call arguments converted to dictionaries
    """
    if not messages:
        return messages
    
    # Create a deep copy to avoid modifying the original
    msgs_copy = copy.deepcopy(messages)
    modified_count = 0
    
    for msg in msgs_copy:
        # Check if the message has tool_calls
        if isinstance(msg, dict) and 'tool_calls' in msg and msg['tool_calls']:
            for tool_call in msg['tool_calls']:
                if isinstance(tool_call, dict) and 'function' in tool_call:
                    if 'arguments' in tool_call['function']:
                        # If arguments is a string, parse it to a dict
                        if isinstance(tool_call['function']['arguments'], str):
                            try:
                                parsed = parse_json_safely(tool_call['function']['arguments'])
                                # If parsing results in an empty dict, remove the key instead
                                if not parsed: 
                                    del tool_call['function']['arguments']
                                    logger.debug("Removed empty arguments key during preprocessing.")
                                else:
                                    tool_call['function']['arguments'] = parsed
                                modified_count += 1
                            except Exception as e:
                                logger.error(f"Error parsing tool call arguments: {e}")
                                # If error, ensure key is removed or set to empty dict
                                if 'arguments' in tool_call['function']:
                                    del tool_call['function']['arguments'] 
    
    if modified_count > 0:
        logger.debug(f"Preprocessed {modified_count} tool call arguments from strings to dicts")
    
    return msgs_copy


def convert_mcp_tools_to_ollama_format(mcp_tools: Union[List[Any], Dict[str, Any], Any]) -> List[OllamaToolType]:
    """
    Convert MCP tool format to Ollama tool format according to the Ollama SDK docs.
    
    Args:
        mcp_tools: Tools in MCP format (list, dict with 'tools' key, or object with 'tools' attribute)
        
    Returns:
        List of tools formatted for Ollama's API
    """
    logger.debug("Converting MCP tools to Ollama format")
    ollama_tools = []

    # Clear the global mapping before processing
    tool_name_mapping.clear()

    # Extract tools from the input based on its type
    tools_list = extract_tools_list(mcp_tools)

    # Process each tool in the list
    if isinstance(tools_list, list):
        for tool_idx, tool in enumerate(tools_list):
            if "name" in tool and "description" in tool:
                # Process valid tool
                ollama_tool = process_single_tool(tool, tool_idx)
                if ollama_tool:
                    ollama_tools.append(ollama_tool)
            else:
                logger.warning(f"Tool missing required attributes: has name = {'name' in tool}, has description = {'description' in tool}")
    else:
        logger.warning(f"Tools list is not a list, it's a {type(tools_list)}")

    logger.debug(f"Converted {len(ollama_tools)} tools to Ollama format")
    return ollama_tools


def extract_tools_list(mcp_tools: Union[List[Any], Dict[str, Any], Any]) -> List[Any]:
    """
    Extract the actual tools list from various possible input formats.
    
    Args:
        mcp_tools: The input that contains tools in some format
        
    Returns:
        List of tools
    """
    if hasattr(mcp_tools, 'tools'):
        tools_list = mcp_tools.tools
        logger.debug("Extracted tools from object.tools attribute")
    elif isinstance(mcp_tools, dict):
        tools_list = mcp_tools.get('tools', [])
        logger.debug("Extracted tools from dict['tools']")
    else:
        tools_list = mcp_tools
        logger.debug(f"Using tools directly from input of type {type(mcp_tools)}")
    
    return tools_list


def process_single_tool(tool: Dict[str, Any], tool_idx: int) -> Optional[OllamaToolType]:
    """
    Process a single tool definition into Ollama format.
    
    Args:
        tool: Tool definition
        tool_idx: Index for logging purposes
        
    Returns:
        Tool in Ollama format or None if processing fails
    """
    try:
        # Store the original name in our mapping
        original_name = tool["name"]
        logger.debug(f"Processing tool [{tool_idx}]: {original_name}")

        # For server_name_tool_name format used in client.py
        server_tool_name = f"{original_name}"
        tool_name_mapping[original_name] = server_tool_name

        # Get parameter properties
        properties, required = extract_tool_parameters(tool)

        # Create tool in Ollama's expected format based on docs
        ollama_tool = {
            "type": "function",
            "function": {
                "name": original_name,
                "description": tool.get("description", ""),
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

        logger.debug(f"Added tool to Ollama format: {original_name}")
        return ollama_tool
    
    except Exception as e:
        logger.error(f"Error processing tool: {e}")
        return None


def extract_tool_parameters(tool: Dict[str, Any]) -> tuple[dict, list]:
    """
    Extract parameter properties and required fields from a tool definition.
    
    Args:
        tool: Tool definition
        
    Returns:
        Tuple of (properties dict, required list)
    """
    properties = {}
    required = []

    if "parameters" in tool:
        if isinstance(tool["parameters"], dict):
            properties = tool["parameters"].get("properties", {})
            required = tool["parameters"].get("required", [])
            logger.debug(f"Tool has parameters: properties={list(properties.keys())}, required={required}")
        else:
            logger.warning(f"Tool parameters not a dict: {type(tool['parameters'])}")
    else:
        logger.debug("Tool has no parameters defined")
        
    return properties, required


def prepare_ollama_options(model_cfg: Dict[str, Any]) -> tuple[Dict[str, Any], Optional[Any], str]:
    """
    Prepare options for Ollama API call.
    
    Args:
        model_cfg: Model configuration
        
    Returns:
        Tuple of (options dict, client object, keep_alive value)
    """
    # Import here to avoid import errors when module is loaded
    from ollama import Client
    
    options = {}
    client = None
    keep_alive_seconds = "0"

    # Set model parameters from config
    if "temperature" in model_cfg:
        options["temperature"] = model_cfg.get("temperature", DEFAULT_TEMPERATURE)
    if "top_k" in model_cfg:
        options["top_k"] = model_cfg.get("top_k")
    if "repetition_penalty" in model_cfg:
        options["repeat_penalty"] = model_cfg.get("repetition_penalty")
    if "max_tokens" in model_cfg:
        options["num_predict"] = model_cfg.get("max_tokens", DEFAULT_MAX_TOKENS)
    if "client" in model_cfg:
        client = Client(host=model_cfg.get("client", DEFAULT_API_HOST))
    if "keep_alive_seconds" in model_cfg:
        keep_alive_seconds = model_cfg.get("keep_alive_seconds") + "s"
        
    return options, client, keep_alive_seconds


def format_tool_calls(response_tool_calls: List[Any]) -> List[Dict[str, Any]]:
    """
    Format tool calls from Ollama response for Dolphin MCP.
    
    Args:
        response_tool_calls: Tool calls from Ollama response
        
    Returns:
        Formatted tool calls for client.py
    """
    tool_calls = []
    
    for i, tool in enumerate(response_tool_calls):
        # Get function details
        func_name = tool.function.name
        func_args = {}
        
        # Extract arguments (should be a dict in the response)
        if hasattr(tool.function, 'arguments'):
            if isinstance(tool.function.arguments, dict):
                func_args = tool.function.arguments
                logger.debug(f"Tool {i} arguments: {func_args}")
            else:
                # If somehow not a dict, try to convert
                if isinstance(tool.function.arguments, str):
                    func_args = parse_json_safely(tool.function.arguments)
                    logger.debug(f"Converted string arguments to dict: {func_args}")
        
        # Format the function name for client.py
        formatted_name = format_function_name(func_name)
        
        # Convert arguments back to a JSON string for client.py
        args_str = json.dumps(func_args) if func_args else "{}"
        
        # Create the tool object in the format expected by client.py
        tool_obj = {
            "id": f"call_ollama_{i}",
            "function": {
                "name": formatted_name,
                "arguments": args_str  # Must be string for client.py
            }
        }
        
        tool_calls.append(tool_obj)
        logger.debug(f"Added tool call: {formatted_name}")
    
    return tool_calls


def format_function_name(func_name: str) -> str:
    """
    Format function name with server prefix if needed.
    
    Args:
        func_name: Original function name
        
    Returns:
        Formatted function name
    """
    formatted_name = func_name
    if "_" not in func_name and tool_name_mapping:
        first_server_prefix = next(iter(tool_name_mapping.values()), "unknown_server")
        formatted_name = f"{first_server_prefix}_{func_name}"
        logger.debug(f"Formatted name: {formatted_name}")
    
    return formatted_name


async def generate_with_ollama(
    conversation: List[MessageType], 
    model_cfg: Dict[str, Any], 
    all_functions: Union[List[Any], Dict[str, Any], Any]
) -> Dict[str, Any]:
    """
    Generate text using Ollama's API.

    Args:
        conversation: The conversation history as a list of message objects
        model_cfg: Configuration for the model including parameters and options
        all_functions: Available functions for the model to call

    Returns:
        Dict containing assistant_text and tool_calls
    """
    logger.debug("===== Starting generate_with_ollama =====")

    # Import required components from Ollama
    try:
        ollama_imports = import_ollama_components()
        if not ollama_imports:
            return {"assistant_text": "Failed to import required Ollama components", "tool_calls": []}
        chat, Client, ResponseError = ollama_imports
    except Exception as e:
        logger.error(f"Unexpected error during Ollama import: {e}")
        return {"assistant_text": f"Unexpected Ollama import error: {str(e)}", "tool_calls": []}

    # Get model name from config
    model_name = model_cfg.get("model", "")
    if not model_name:
        error_msg = "Model name is required but was not provided in configuration"
        logger.error(error_msg)
        return {"assistant_text": error_msg, "tool_calls": []}
        
    logger.debug(f"Using model: {model_name}")

    # Convert tools to Ollama format
    converted_all_functions = convert_mcp_tools_to_ollama_format(all_functions)

    # Prepare options dictionary for Ollama
    options, client, keep_alive_seconds = prepare_ollama_options(model_cfg)

    # Preprocess conversation messages to ensure arguments are dictionaries
    processed_conversation = preprocess_messages(conversation)

    # Define a baseline chat params dict
    chat_params = {
        "model": model_name,
        "messages": processed_conversation,
        "options": options,
        "stream": False,
        "tools": converted_all_functions
    }

    # Add keep_alive if needed
    if keep_alive_seconds != "0":
        chat_params["keep_alive"] = keep_alive_seconds

    logger.debug(f"Chat parameters prepared with {len(converted_all_functions)} tools")

    # Log conversation for debugging (abbreviated)
    log_conversation_sample(processed_conversation)

    # Call Ollama API
    try:
        # Make the API call
        response = await call_ollama_api(chat, client, chat_params)
        if isinstance(response, dict) and "assistant_text" in response:
            # This is an error response from call_ollama_api
            return response
            
        # Extract assistant text
        assistant_text = response.message.content or ""
        logger.debug(f"Assistant text (abbreviated): {assistant_text[:100]}...")
        
        # Process tool calls if present
        tool_calls = []
        if hasattr(response.message, 'tool_calls') and response.message.tool_calls:
            logger.debug(f"Found {len(response.message.tool_calls)} tool calls in response")
            tool_calls = format_tool_calls(response.message.tool_calls)
        
        return {"assistant_text": assistant_text, "tool_calls": tool_calls}
        
    except Exception as e:
        logger.error(f"Unexpected error in generate_with_ollama: {e}")
        traceback.print_exc()
        return {"assistant_text": f"Unexpected error: {str(e)}", "tool_calls": []}


def import_ollama_components() -> Optional[tuple]:
    """
    Import the necessary Ollama components.
    
    Returns:
        Tuple of (chat, Client, ResponseError) or None if import fails
    """
    try:
        from ollama import chat, Client, ResponseError
        logger.debug("Imported Ollama SDK successfully")
        
        # Try to get the version if available
        try:
            import importlib.metadata
            ollama_version = importlib.metadata.version('ollama')
            logger.debug(f"Ollama SDK version: {ollama_version}")
        except (ImportError, importlib.metadata.PackageNotFoundError):
            logger.debug("Could not determine Ollama SDK version")
            
        return chat, Client, ResponseError
    except ImportError as e:
        logger.error(f"Failed to import Ollama SDK: {e}")
        return None


def log_conversation_sample(conversation: List[MessageType]) -> None:
    """
    Log a sample of the conversation for debugging.
    
    Args:
        conversation: The conversation to log
    """
    if not conversation:
        return
        
    try:
        if len(conversation) > 0:
            first_msg = json.dumps(conversation[0])[:150]
            logger.debug(f"First message (abbreviated): {first_msg}...")
        
        if len(conversation) > 1:
            last_msg = json.dumps(conversation[-1])[:150]
            logger.debug(f"Last message (abbreviated): {last_msg}...")
    except Exception as e:
        logger.debug(f"Could not log conversation sample: {e}")


async def call_ollama_api(
    chat: Callable, 
    client: Optional[Any], 
    chat_params: Dict[str, Any]
) -> Union[ChatResponse, Dict[str, Any]]:
    """
    Call the Ollama API using httpx to manually handle the response and fix potential issues
    before Pydantic validation.

    Args:
        chat: The chat function from ollama (unused, kept for signature compatibility for now)
        client: Optional ollama client object to get host info
        chat_params: Parameters for the chat call

    Returns:
        Either a parsed ChatResponse object or an error dict
    """
    logger.debug("Calling Ollama API via httpx...")

    # Determine host and construct URL
    host = DEFAULT_API_HOST
    if client and hasattr(client._client, 'base_url'):
        host = client._client.base_url
    api_url = f"{host}/api/chat"
    logger.debug(f"Target API URL: {api_url}")

    try:
        async with httpx.AsyncClient(timeout=600.0) as http_client: # Increased timeout
            http_response = await http_client.post(api_url, json=chat_params)
            http_response.raise_for_status() # Raise exception for 4xx/5xx errors
            
            raw_response_data = http_response.json()
            logger.debug("Received raw JSON response from Ollama API.")

            # --- Manual Fix for Missing 'arguments' ---
            if 'message' in raw_response_data and 'tool_calls' in raw_response_data['message'] and raw_response_data['message']['tool_calls']:
                corrected_count = 0
                for tool_call in raw_response_data['message']['tool_calls']:
                    if isinstance(tool_call, dict) and 'function' in tool_call:
                        if 'arguments' not in tool_call['function']:
                            tool_call['function']['arguments'] = {}
                            corrected_count += 1
                            logger.debug(f"Manually added missing 'arguments: {{}}' to tool call: {tool_call.get('function', {}).get('name')}")
                if corrected_count > 0:
                     logger.info(f"Corrected {corrected_count} tool calls with missing 'arguments'.")
            # --- End Manual Fix ---

            # Attempt to parse the corrected data using the SDK's Pydantic model
            try:
                parsed_response = ChatResponse(**raw_response_data)
                logger.debug("Successfully parsed corrected JSON into ChatResponse model.")
                return parsed_response
            except ValidationError as pydantic_error:
                logger.error(f"Pydantic validation failed even after manual correction: {pydantic_error}")
                logger.debug(f"Corrected JSON data that failed validation: {raw_response_data}")
                return {
                     "assistant_text": f"Ollama SDK Validation Error after manual correction: {str(pydantic_error)}",
                     "tool_calls": []
                 }

    except httpx.HTTPStatusError as e:
        logger.error(f"Ollama API HTTP Error: {e.response.status_code} - {e.response.text}")
        # Try to parse error details from response if possible
        error_detail = e.response.text
        try:
            error_json = e.response.json()
            error_detail = error_json.get('error', error_detail)
        except Exception:
            pass # Keep original text if JSON parsing fails
        return {"assistant_text": f"Ollama API HTTP Error {e.response.status_code}: {error_detail}", "tool_calls": []}
    except httpx.RequestError as e:
        logger.error(f"Ollama API Request Error: {e}")
        return {"assistant_text": f"Ollama API Request Error: {str(e)}", "tool_calls": []}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON response from Ollama API: {e}")
        return {"assistant_text": f"Ollama API JSON Decode Error: {str(e)}", "tool_calls": []}
    except ValidationError as e: # Catch Pydantic errors during initial raw parsing if they occur
        # This specific check might be less likely now, but kept for safety
        error_str = str(e)
        logger.error(f"Caught Pydantic validation error during httpx handling: {e}")
        return {
            "assistant_text": f"Ollama SDK Validation Error during httpx handling: {error_str}",
            "tool_calls": []
        }
    except Exception as e:
        logger.error(f"Unexpected error during Ollama API call via httpx: {e}")
        traceback.print_exc()
        return {"assistant_text": f"Unexpected error during httpx API call: {str(e)}", "tool_calls": []}
