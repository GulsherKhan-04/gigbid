# 1. One marketplace port, MCP underneath
Decision: the graph depends only on `MarketplacePort`; GigSim is reached through our Marketplace MCP server, Upwork through its official MCP server.
Why: R1/R2, and live mode becomes a config switch. Cost: one extra hop for GigSim calls.
