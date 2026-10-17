# examples

## Parallel web search

[Parallel Search MCP](https://docs.parallel.ai/integrations/mcp/search-mcp)
provides web search and page fetching without a Parallel account or API key.
Anonymous search uses Fast mode and is rate limited for light use.
The [example configuration](parallel-search-mcp.json) uses
[`mcp-remote`](https://github.com/geelen/mcp-remote) to bridge Dolphin's stdio
client to the remote Streamable HTTP endpoint. The bridge honors `HTTP_PROXY`,
`HTTPS_PROXY`, and `NO_PROXY` when set.

Use Python 3.11+ and Node.js 22+ with `npm`/`npx` on your PATH. From the repository
root, install Dolphin in your Python environment and cache the pinned bridge:

```bash
python -m pip install -e . lmstudio aiohttp
npm exec --yes --package=mcp-remote@0.15.1 -- node --version
```

The extra Python packages are imported by Dolphin's existing providers. Caching
the bridge first keeps its initial download outside Dolphin's 10-second server
startup timeout.

Choose a tool-capable model from `config.yml`. This command uses its `gpt-4o`
entry and requires your OpenAI API key in `.env`; replace `--model gpt-4o` with
your configured local model to use a local provider instead:

```bash
python -P -m dolphin_mcp.cli --config config.yml --mcp-config examples/parallel-search-mcp.json --model gpt-4o "Use parallel_web_search to find the official Python asyncio TaskGroup documentation, then parallel_web_fetch to read the relevant page. Summarize TaskGroup and cite the source URL."
```

Run the Python module as shown to invoke the asynchronous CLI. The `-P` flag
keeps the root `dolphin_mcp.py` script from shadowing the installed package.
Dolphin should
report `[OK] parallel` and expose `parallel_web_search` and `parallel_web_fetch`
to the model. Tool use depends on the selected model. This example selects only
Parallel for this invocation; to keep other servers available, copy the
`parallel` entry into your own `mcpServers` object alongside them.

## sqlite

```dolphin-mcp-cli --mcp-config examples/sqlite-mcp.json  --model dolphin "Explore the database, and choose one random row - and write a story about it"```

### Output

```
[OK] dolphin-demo-database-sqlite

View result from list_tables from dolphin-demo-database-sqlite {}
{
  "content": [
    {
      "type": "text",
      "text": "[{'name': 'dolphin_species'}, {'name': 'evolutionary_relationships'}, {'name': 'table_name'}]"
    }
  ],
  "isError": false
}

View result from read_query from dolphin-demo-database-sqlite {"query": "SELECT * FROM dolphin_species ORDER BY RANDOM() LIMIT 1"}
{
  "content": [
    {
      "type": "text",
      "text": "[{'id': 3, 'common_name': 'Common Dolphin', 'scientific_name': 'Delphinus delphis', 'family': 'Delphinidae', 'habitat': 'Oceanic', 'average_length_meters': 2.3, 'average_weight_kg': 110.0, 'average_lifespan_years': 35, 'conservation_status': 'Least Concern', 'population_estimate': 'Unknown', 'evolutionary_ancestor': 'Kentriodontids', 'description': 'Known for their distinctive colorful pattern and hourglass pattern on their sides.'}]"
    }
  ],
  "isError": false
}

In the vast expanse of the ocean, where the sun kisses the water in a golden embrace, there swims a creature of grace and beauty. Meet the Common Dolphin, Delphinus delphis, a marvel of nature that has captivated human hearts for centuries.

Our story begins with an individual dolphin, one whose life is as mysterious as the depths from which it emerges. This particular dolphin, measuring 2.3 meters in length and weighing around 110 kilograms, is a testament to the resilience and adaptability of its species. It belongs to the family Delphinidae, a group renowned for their intelligence and playful nature.

The Common Dolphin's habitat is as boundless as the ocean itself, preferring the open waters where it can swim freely without constraint. Its average lifespan of 35 years speaks of a life filled with adventure and exploration, a journey through the highs and lows of the sea.

But what sets this dolphin apart is not just its physical attributes or its habitat; it is the story of its evolutionary past. This dolphin's ancestors were once Kentriodontids, ancient creatures that roamed the oceans millions of years ago. Over time, they evolved into the sleek and sophisticated beings we know today.

As our dolphin glides through the water, its sides adorned with a distinctive colorful pattern and an hourglass shape, it is a living testament to the power of evolution. Its conservation status as 'Least Concern' is a beacon of hope, a sign that despite the challenges faced by many marine species, this one thrives.

Yet, there is still much we do not know about our dolphin friend. The population estimate remains a mystery, a secret hidden beneath the waves. But what we do know is enough to inspire awe and wonder.

In the heart of the ocean, where the unknown awaits around every corner, our Common Dolphin swims on. Its story is one of survival, adaptation, and beauty, a reminder of the magic that lies just beyond our reach in the depths of the sea.

```

## filesystem-fetch

```dolphin-mcp-cli --mcp-config examples/filesystem-fetch-mcp.json --model gpt-4o "Read ./examples/stocklist.txt and fetch https://finance.yahoo.com/topic/stock-market-news/. If there is positive news about any of the stocks in the list, advise me to buy that stock.  if there is negative news about any of the stocks in the list, advise me to sell that stock."```

### Output

```
[OK] filesystem
[OK] fetch

View result from read_file from filesystem {"path": "./examples/stocklist.txt"}
{
  "content": [
    {
      "type": "text",
      "text": "AAPL\nMSFT\nNVDA\nAMZN\nGOOGL\nTSLA\nJPM\nJNJ\nXOM\nDIS"
    }
  ]
}

View result from fetch from fetch {"url": "https://finance.yahoo.com/topic/stock-market-news/", "max_length": 10000}
{
  "content": [
    {
      "type": "text",
      "text": "Contents of https://finance.yahoo.com/topic/stock-market-news/:\n* [![Most baby boomers can\u2019t afford assisted living and are weighing on the housing market by staying in their homes, \u2018Oracle of Wall Street\u2019 says](https://s.yimg.com/uu/api/res/1.2/ivl4tU10JsMMXXGZpY5Edw--~B/Zmk9c3RyaW07aD0xMjY7cT04MDt3PTE2ODthcHBpZD15dGFjaHlvbg--/https://media.zenfs.com/en/fortune_175/038149f7d7a61eab6b1ffba41dcf758c.cf.webp)](https://finance.yahoo.com/news/most-baby-boomers-t-afford-220048092.html \"Most baby boomers can\u2019t afford assisted living and are weighing on the housing market by staying in their homes, \u2018Oracle of Wall Street\u2019 says\")\n\n  [### Most baby boomers can\u2019t afford assisted living and are weighing on the housing market by staying in their homes, \u2018Oracle of Wall Street\u2019 says\n\n  \"This is one of the problems with the housing inventory. They're staying in their houses longer because they can't afford to move out.\"](https://finance.yahoo.com/news/most-baby-boomers-t-afford-220048092.html \"Most baby boomers can\u2019t afford assisted living and are weighing on the housing market by staying in their homes, \u2018Oracle of Wall Street\u2019 says\")\n\n  Fortune 5 hours ago\n* [![Digital marketing used to be about clicks, but the rise of ChatGPT means it\u2019s \u2018now all about winning the mentions\u2019](https://s.yimg.com/uu/api/res/1.2/anetyzotfpwoXbd5aEwWOQ--~B/Zmk9c3RyaW07aD0xMjY7cT04MDt3PTE2ODthcHBpZD15dGFjaHlvbg--/https://media.zenfs.com/en/fortune_175/3215f088034585320facdda4cd4781b5.cf.webp)](https://finance.yahoo.com/news/digital-marketing-used-clicks-rise-192813332.html \"Digital marketing used to be about clicks, but the rise of ChatGPT means it\u2019s \u2018now all about winning the mentions\u2019\")\n\n  [### Digital marketing used to be about clicks, but the rise of ChatGPT means it\u2019s \u2018now all about winning the mentions\u2019\n\n  Brand credibility is now a crucial aspect of marketing campaigns, and companies must couple that with storytelling, experts say.](https://finance.yahoo.com/news/digital-marketing-used-clicks-rise-192813332.html \"Digital marketing used to be about clicks, but the rise of ChatGPT means it\u2019s \u2018now all about winning the mentions\u2019\")\n\n  Fortune 8 hours ago\n* [![Wall Street plays long game as deals go private](https://s.yimg.com/uu/api/res/1.2/vJQcQkoYRNIOX.AqCSn5og--~B/Zmk9c3RyaW07aD0xMjY7cT04MDt3PTE2ODthcHBpZD15dGFjaHlvbg--/https://s.yimg.com/os/creatr-uploaded-images/2025-05/800d4880-2dda-11f0-abfe-fd1ab4279da0.cf.webp)](https://finance.yahoo.com/news/wall-street-plays-long-game-190000469.html \"Wall Street plays long game as deals go private\")\n\n  [### Wall Street plays long game as deals go private\n\n  (Bloomberg) -- A KKR & Co. debt sale shows how far Wall Street is willing to go to keep leveraged underwriting business from slipping away to private credit after periods of turmoil.Most Read from BloombergAs Trump Reshapes Housing Policy, Renters Face Rollback of RightsIs Trump\u2019s Plan to Reopen the Notorious Alcatraz Prison Realistic?What\u2019s Behind the Rise in Serious Injuries on New York City\u2019s Streets?A New Central Park Amenity, Tailored to Its East Harlem NeighborsNYC Warns of 17% Drop in For](https://finance.yahoo.com/news/wall-street-plays-long-game-190000469.html \"Wall Street plays long game as deals go private\")\n\n  Bloomberg 8 hours ago\n\n  [AAPL](/quote/AAPL/ \"AAPL\")  [GM](/quote/GM/ \"GM\")\n* [![A midsize city in upstate New York is the country\u2019s toughest housing market this spring](https://s.yimg.com/uu/api/res/1.2/XLgKcrtPz1yIun2t0nJ6ew--~B/Zmk9c3RyaW07aD0xMjY7cT04MDt3PTE2ODthcHBpZD15dGFjaHlvbg--/https://s.yimg.com/os/creatr-images/2020-06/17612370-a855-11ea-9fde-d414f241d6d0.cf.webp)](https://finance.yahoo.com/news/a-midsize-city-in-upstate-new-york-is-the-countrys-toughest-housing-market-this-spring-143308210.html \"A midsize city in upstate New York is the country\u2019s toughest housing market this spring\")\n\n  [### A midsize city in upstate New York is the country\u2019s toughest housing market this spring\n\n  The median home in Rochester, N.Y. sells for just $225,000, and competition to buy is steeper than in San Francisco and Boston.](https://finance.yahoo.com/news/a-midsize-city-in-upstate-new-york-is-the-countrys-toughest-housing-market-this-spring-143308210.html \"A midsize city in upstate New York is the country\u2019s toughest housing market this spring\")\n\n  Yahoo Finance 13 hours ago\n* [![For Exhausted Stock Market Pros the Choice Is Buy or Stay Home](https://s.yimg.com/uu/api/res/1.2/M2ORaeWGrV9FiUrQT8mQ1Q--~B/Zmk9c3RyaW07aD0xMjY7cT04MDt3PTE2ODthcHBpZD15dGFjaHlvbg--/https://media.zenfs.com/en/bloomberg_holding_pen_162/5a26f0563703088194cdc654067a177c.cf.webp)](https://finance.yahoo.com/news/exhausted-stock-market-pros-choice-120007868.html \"For Exhausted Stock Market Pros the Choice Is Buy or Stay Home\")\n\n  [### For Exhausted Stock Market Pros the Choice Is Buy or Stay Home\n\n  (Bloomberg) -- The stock market\u2019s stunning rebound over the last month has largely been driven by Main Street investors buying the dip in everything in sight while professional money managers ditched US stocks, spooked by mounting fears of slowing economic growth and trade war disruptions.Most Read from BloombergAs Trump Reshapes Housing Policy, Renters Face Rollback of RightsIs Trump\u2019s Plan to Reopen the Notorious Alcatraz Prison Realistic?What\u2019s Behind the Rise in Serious Injuries on New York](https://finance.yahoo.com/news/exhausted-stock-market-pros-choice-120007868.html \"For Exhausted Stock Market Pros the Choice Is Buy or Stay Home\")\n\n  Bloomberg 15 hours ago\n\n  [NVDA](/quote/NVDA/ \"NVDA\")  [JPM](/quote/JPM/ \"JPM\")\n* [![The Graduating Class of 2025 is Entering an Uncertain Job Market](https://s.yimg.com/uu/api/res/1.2/5lk1RnfIE7ChAECeg9FS4A--~B/Zmk9c3RyaW07aD0xMjY7cT04MDt3PTE2ODthcHBpZD15dGFjaHlvbg--/https://media.zenfs.com/en/investopedia_245/d755d1738727234ebac204193e26c017.cf.webp)](https://finance.yahoo.com/news/graduating-class-2025-entering-uncertain-104600208.html \"The Graduating Class of 2025 is Entering an Uncertain Job Market\")\n\n  [### The Graduating Class of 2025 is Entering an Uncertain Job Market\n\n  As an estimated 2 million college graduates hope to find a job this spring, they enter a cooling job market in which employers are bracing for the impact of President Donald Trump's tariffs.](https://finance.yahoo.com/news/graduating-class-2025-entering-uncertain-104600208.html \"The Graduating Class of 2025 is Entering an Uncertain Job Market\")\n\n  Investopedia 17 hours ago\n* [![Best money market account rates today, May 10, 2025 (best account provides 4.41% APY)](https://s.yimg.com/uu/api/res/1.2/GJKwz40mSpK0EHAJt50HHA--~B/Zmk9c3RyaW07aD0xMjY7cT04MDt3PTE2ODthcHBpZD15dGFjaHlvbg--/https://s.yimg.com/os/creatr-uploaded-images/2025-04/678943f0-1cdb-11f0-bfb7-b3f563b0ea90.cf.webp)](https://finance.yahoo.com/personal-finance/banking/article/best-money-market-account-rates-today-saturday-may-10-2025-100027028.html \"Best money market account rates today, May 10, 2025 (best account provides 4.41% APY)\")\n\n  [### Best money market account rates today, May 10, 2025 (best account provides 4.41% APY)\n\n  If you\u2019re searching for today\u2019s best money market account rates, we\u2019ve narrowed down some of the top offers. Learn more about money market account rates today.](https://finance.yahoo.com/personal-finance/banking/article/best-money-market-account-rates-today-saturday-may-10-2025-100027028.html \"Best money market account rates today, May 10, 2025 (best account provides 4.41% APY)\")\n\n  Yahoo Personal Finance 17 hours ago\n* [![Trump is about to drop a multi-trillion bomb on the stock market](https://s.yimg.com/uu/api/res/1.2/lpyIXUVboedRXtbjDbUQzw--~B/Zmk9c3RyaW07aD0xMjY7cT04MDt3PTE2ODthcHBpZD15dGFjaHlvbg--/https://media.zenfs.com/en/the_telegraph_258/0c9f43024792b12fa2baddc0067ea7d2.cf.webp)](https://finance.yahoo.com/news/trump-big-beautiful-bill-threatens-070000728.html \"Trump is about to drop a multi-trillion bomb on the stock market\")\n\n  [### Trump is about to drop a multi-trillion bomb on the stock market\n\n  Donald Trump has branded it the \u201cbig beautiful bill\u201d that will save millions of jobs and boost Americans\u2019 take-home pay by up to $5,000 (\u00a33,700) a year.](https://finance.yahoo.com/news/trump-big-beautiful-bill-threatens-070000728.html \"Trump is about to drop a multi-trillion bomb on the stock market\")\n\n  The Telegraph 20 hours ago\n* [![Why BofA says more trade deals can't keep the stock market rally alive](https://s.yimg.com/uu/api/res/1.2/NfHh3CE3DVMXgxlFGyk17A--~B/Zmk9c3RyaW07aD0xMjY7cT04MDt3PTE2ODthcHBpZD15dGFjaHlvbg--/https://media.zenfs.com/en/business_insider_articles_888/362d8df0e2705d4a4c94696e71e3c528.cf.webp)](https://finance.yahoo.com/news/why-bofa-says-more-trade-001310446.html \"Why BofA says more trade deals can't keep the stock market rally alive\")\n\n  [### Why BofA says more trade deals can't keep the stock market rally alive\n\n  The S&P 500 has rallied sharply since April lows, but investors should be prepared for the gains to fade as more trade deals are announced, BofA said.](https://finance.yahoo.com/news/why-bofa-says-more-trade-001310446.html \"Why BofA says more trade deals can't keep the stock market rally alive\")\n\n  Business Insider yesterday\n* [![From a recession to the impact of AI, 4 predictions from Wall Street's 'Dr. Doom'](https://s.yimg.com/uu/api/res/1.2/jxj_4JI_o7FGy7HL965edQ--~B/Zmk9c3RyaW07aD0xMjY7cT04MDt3PTE2ODthcHBpZD15dGFjaHlvbg--/https://media.zenfs.com/en/business_insider_articles_888/ac493b3a8a7fca88c3441b85cdff65c4.cf.webp)](https://finance.yahoo.com/news/recession-impact-ai-4-predictions-225612935.html \"From a recession to the impact of AI, 4 predictions from Wall Street's 'Dr. Doom'\")\n\n  [### From a recession to the impact of AI, 4 predictions from Wall Street's 'Dr. Doom'\n\n  The US could enter a mild recession by the end of 2025, according to Wall Street's \"Dr. Doom\" economist, Nouriel Roubini.](https://finance.yahoo.com/news/recession-impact-ai-4-predictions-225612935.html \"From a recession to the impact of AI, 4 predictions from Wall Street's 'Dr. Doom'\")\n\n  Business Insider yesterday\n\n<error>Content truncated. Call the fetch tool with a start_index of 10000 to get more content.</error>"
    }
  ],
  "isError": false
}

From the content available, there are mentions of some of the stocks in your list:

1. **AAPL (Apple Inc.)** - The article mentions AAPL in the context of Wall Street playing a long game as deals go private. No specific positive or negative sentiment is mentioned.

2. **NVDA (NVIDIA Corporation)** and **JPM (JPMorgan Chase & Co.)** - Both are mentioned in the context of the stock market's stunning rebound driven by Main Street investors. There is a sense of positivity here about the market, which could imply a positive sentiment towards these stocks.

Based on the articles retrieved, there isn't any explicit negative news about stocks from your list. However, there is a positive implication for NVDA and JPM as the stock market is rebounding due to increased activity from Main Street investors and implied positivity about specific stocks. Therefore:

- **Advice**: Consider buying NVDA and JPM due to the positive sentiment in the coverage related to these stocks. 

If you want more detailed news, let me know so I can fetch additional content.
```


