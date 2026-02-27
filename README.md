# STACK SEARCH // Extended Boolean Engine

Advanced information retrieval system built for **BI-VWM** course at **FIT CTU**. This engine processes 5,000 Stack Overflow Q&A threads using an **Extended Boolean Model (p-norm)**.

## Key Features

- **P-Norm Implementation**: Supports fuzzy-to-strict logical evaluation by adjusting the $p$ parameter.
- **Advanced Preprocessing**: Optimized tokenization with a specialized **Stemming Exception List** for technical terms (AWS, SQL, .NET, etc.).
- **Inverted Index**: High-speed retrieval using TF-IDF weighted vector space.
- **Brutalist UI**: Clean, high-contrast interface with real-time query highlighting and mathematical guidance.



## Algorithmic Insights

### The p-Norm Power
The engine allows users to transition between:
1. **$p = 1$ (Soft Logic)**: Acts as an arithmetic mean of term weights. High recall.
2. **$p = 2$ (Euclidean)**: Standard balanced retrieval.
3. **$p \to \infty$ (Strict Boolean)**: Mimics pure Boolean AND/OR logic. High precision.

### Technical Term Integrity
Unlike standard search engines, we implemented a custom filter to protect technical identifiers. For example, `AWS` is preserved as a literal instead of being stemmed to `aw`, preventing collisions with words like `away`.

