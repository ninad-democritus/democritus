# RAG (Retrieval-Augmented Generation) Implementation Guide

## Overview

This document details how to implement semantic search over metadata using RAG embeddings generated from the Context Agent's output. The goal is to enable natural language queries like "Where is customer email stored?" or "Show me all PII fields" to return relevant metadata objects.

##

 What are RAG Embeddings?

**RAG (Retrieval-Augmented Generation)** embeddings are vector representations of text that enable semantic similarity search. Unlike keyword search, vector search finds conceptually similar content even without exact word matches.

**Example:**
- Query: "customer contact info"
- Match: `Customer.email` column (even though "contact info" doesn't appear in text)
- Reason: Embedding vectors capture semantic meaning

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Context Agent Output (Minimal Schema with Descriptions)    │
│  - Entities with business narratives                        │
│  - Columns with semantic descriptions                       │
│  - Relationships with contextual explanations               │
│  - Glossary terms with enriched definitions                 │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  Embedding Generation Service (data-pipeline)               │
│  - Extract text from descriptions                           │
│  - Generate vector embeddings (sentence-transformers)       │
│  - Create metadata index                                    │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  Vector Database (Qdrant / Weaviate / Chroma)              │
│  - Store embeddings with metadata                           │
│  - Enable similarity search                                 │
│  - Support filtering by type, domain, tags                  │
└───────────────────────┬─────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│  Search API / Query Service                                 │
│  - Accept natural language queries                          │
│  - Generate query embeddings                                │
│  - Retrieve top-k similar items                             │
│  - Return ranked results                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 1: Embedding Model Selection

### Recommended: `sentence-transformers/all-MiniLM-L6-v2`

**Pros:**
- Fast (384-dimensional embeddings)
- Good semantic understanding
- Already used by Aligner and Glossary agents (consistency)
- Open-source, can run locally

**Alternative: `text-embedding-ada-002` (OpenAI)**

**Pros:**
- Highest quality embeddings
- 1536 dimensions

**Cons:**
- API cost
- Requires internet connectivity

**For this project, stick with `sentence-transformers/all-MiniLM-L6-v2` for consistency.**

---

## Step 2: Text Extraction from Minimal Schema

### What to Embed

From the Context Agent output, embed the following:

#### 1. Entity Embeddings

```python
def extract_entity_text(entity):
    """Extract embeddable text from entity"""
    
    # Combine multiple text fields for rich context
    text_parts = [
        f"Table: {entity['displayName']}",
        f"Type: {entity['tableType']}",
        f"Description: {entity['description']}",
    ]
    
    # Add synonyms
    if entity.get('synonyms'):
        text_parts.append(f"Also known as: {', '.join(entity['synonyms'])}")
    
    # Add tags for context
    if entity.get('tags'):
        text_parts.append(f"Classifications: {', '.join(entity['tags'])}")
    
    return " | ".join(text_parts)

# Example output:
# "Table: Orders | Type: Fact | Description: The Orders table serves as the central fact table for sales transactions in the Sales & Billing domain. Each record represents a single customer order... | Also known as: Sales Orders, Transactions | Classifications: DataDomain.Fact"
```

**Metadata to Store with Embedding:**
```python
{
    "id": "entity:orders",
    "type": "entity",
    "name": "orders",
    "displayName": "Orders",
    "tableType": "Fact",
    "tags": ["DataDomain.Fact"],
    "confidence": 0.89
}
```

#### 2. Column Embeddings

```python
def extract_column_text(column, entity):
    """Extract embeddable text from column"""
    
    text_parts = [
        f"Column: {entity['displayName']}.{column['displayName']}",
        f"Type: {column['dataTypeDisplay']}",
        f"Description: {column['description']}",
    ]
    
    # Add synonyms
    if column.get('synonyms'):
        text_parts.append(f"Also known as: {', '.join(column['synonyms'])}")
    
    # Add tags
    if column.get('tags'):
        text_parts.append(f"Classifications: {', '.join(column['tags'])}")
    
    return " | ".join(text_parts)

# Example output:
# "Column: Orders.Customer Identifier | Type: varchar(36) | Description: References the customer who placed the order, establishing a link to the Customer dimension table. This foreign key enables customer-level analytics... | Also known as: Customer Reference, Client ID | Classifications: Identifier.Foreign"
```

**Metadata to Store:**
```python
{
    "id": "column:orders.customer_id",
    "type": "column",
    "entity": "orders",
    "column": "customer_id",
    "displayName": "Customer Identifier",
    "dataType": "VARCHAR",
    "tags": ["Identifier.Foreign"],
    "confidence": 0.88
}
```

#### 3. Relationship Embeddings

```python
def extract_relationship_text(relationship):
    """Extract embeddable text from relationship"""
    
    text_parts = [
        f"Relationship: {relationship['fromEntity']} to {relationship['toEntity']}",
        f"Type: {relationship['cardinality']}",
        f"Description: {relationship['description']}",
    ]
    
    return " | ".join(text_parts)

# Example output:
# "Relationship: orders to customer | Type: MANY_TO_ONE | Description: Each order record is associated with exactly one customer through the customer_id reference column, establishing a confirmed many-to-one relationship..."
```

**Metadata to Store:**
```python
{
    "id": "relationship:orders_to_customer",
    "type": "relationship",
    "fromEntity": "orders",
    "toEntity": "customer",
    "cardinality": "MANY_TO_ONE",
    "confidence": 0.87
}
```

#### 4. Glossary Term Embeddings

```python
def extract_glossary_term_text(term, glossary):
    """Extract embeddable text from glossary term"""
    
    text_parts = [
        f"Term: {term['displayName']}",
        f"Domain: {glossary['displayName']}",
        f"Description: {term['description']}",  # Already includes contextual narrative
    ]
    
    # Add synonyms
    if term.get('synonyms'):
        text_parts.append(f"Synonyms: {', '.join(term['synonyms'])}")
    
    # Add related terms
    if term.get('relatedTerms'):
        text_parts.append(f"Related: {', '.join(term['relatedTerms'])}")
    
    return " | ".join(text_parts)

# Example output:
# "Term: Customer | Domain: Sales & Billing | Description: An individual or organization that purchases goods or services. In this system, customers are tracked in the Customer dimension table with 10,000 records... | Synonyms: Client, Buyer | Related: Order, Revenue"
```

**Metadata to Store:**
```python
{
    "id": "term:Customer",
    "type": "glossary_term",
    "term": "Customer",
    "domain": "Sales & Billing",
    "tags": ["DataDomain.Dimension"]
}
```

---

## Step 3: Embedding Generation Implementation

### Using sentence-transformers

```python
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any

class EmbeddingGenerator:
    """Generate embeddings for metadata objects"""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize embedding model"""
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
    
    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generate embeddings for a list of texts
        
        Args:
            texts: List of text strings
            
        Returns:
            numpy array of shape (len(texts), embedding_dim)
        """
        return self.model.encode(texts, show_progress_bar=True)
    
    def generate_single_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a single text"""
        return self.model.encode([text])[0]


def generate_embeddings_from_minimal_schema(minimal_schema: Dict[str, Any]):
    """
    Generate all embeddings from Context Agent output
    
    Args:
        minimal_schema: Output from Context Agent
        
    Returns:
        List of embedding objects ready for vector DB
    """
    generator = EmbeddingGenerator()
    embeddings = []
    
    # 1. Entity embeddings
    for entity in minimal_schema["entities"]:
        text = extract_entity_text(entity)
        embedding = generator.generate_single_embedding(text)
        
        embeddings.append({
            "id": f"entity:{entity['name']}",
            "text": text,
            "embedding": embedding.tolist(),  # Convert to list for JSON serialization
            "metadata": {
                "type": "entity",
                "name": entity["name"],
                "displayName": entity["displayName"],
                "tableType": entity["tableType"],
                "tags": entity.get("tags", []),
                "confidence": entity.get("confidence")
            }
        })
    
    # 2. Column embeddings
    for entity in minimal_schema["entities"]:
        for column in entity["columns"]:
            text = extract_column_text(column, entity)
            embedding = generator.generate_single_embedding(text)
            
            embeddings.append({
                "id": f"column:{entity['name']}.{column['name']}",
                "text": text,
                "embedding": embedding.tolist(),
                "metadata": {
                    "type": "column",
                    "entity": entity["name"],
                    "column": column["name"],
                    "displayName": column["displayName"],
                    "dataType": column["dataType"],
                    "tags": column.get("tags", []),
                    "confidence": column.get("confidence")
                }
            })
    
    # 3. Relationship embeddings
    for relationship in minimal_schema["relationships"]:
        text = extract_relationship_text(relationship)
        embedding = generator.generate_single_embedding(text)
        
        embeddings.append({
            "id": f"relationship:{relationship['fromEntity']}_to_{relationship['toEntity']}",
            "text": text,
            "embedding": embedding.tolist(),
            "metadata": {
                "type": "relationship",
                "fromEntity": relationship["fromEntity"],
                "toEntity": relationship["toEntity"],
                "cardinality": relationship["cardinality"],
                "confidence": relationship.get("confidence")
            }
        })
    
    # 4. Glossary term embeddings
    for glossary in minimal_schema["glossaries"]:
        for term in glossary["terms"]:
            text = extract_glossary_term_text(term, glossary)
            embedding = generator.generate_single_embedding(text)
            
            embeddings.append({
                "id": f"term:{term['name']}",
                "text": text,
                "embedding": embedding.tolist(),
                "metadata": {
                    "type": "glossary_term",
                    "term": term["name"],
                    "domain": glossary["displayName"],
                    "tags": term.get("tags", [])
                }
            })
    
    return embeddings
```

---

## Step 4: Vector Database Storage

### Option 1: Qdrant (Recommended)

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

class QdrantVectorStore:
    """Store embeddings in Qdrant vector database"""
    
    def __init__(self, host: str = "localhost", port: int = 6333):
        """Initialize Qdrant client"""
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = "metadata_embeddings"
        self.embedding_dim = 384  # for all-MiniLM-L6-v2
    
    def create_collection(self):
        """Create collection if it doesn't exist"""
        self.client.recreate_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.embedding_dim,
                distance=Distance.COSINE
            )
        )
    
    def insert_embeddings(self, embeddings: List[Dict[str, Any]]):
        """Insert embeddings into Qdrant"""
        points = []
        
        for idx, emb in enumerate(embeddings):
            point = PointStruct(
                id=idx,
                vector=emb["embedding"],
                payload={
                    "object_id": emb["id"],
                    "text": emb["text"],
                    **emb["metadata"]
                }
            )
            points.append(point)
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
    
    def search(self, query_embedding: np.ndarray, limit: int = 10, 
              filters: Dict[str, Any] = None):
        """
        Search for similar embeddings
        
        Args:
            query_embedding: Query vector
            limit: Number of results
            filters: Metadata filters (e.g., {"type": "column"})
            
        Returns:
            List of search results
        """
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding.tolist(),
            limit=limit,
            query_filter=filters  # Can filter by metadata
        )
        
        return [
            {
                "id": hit.payload["object_id"],
                "score": hit.score,
                "text": hit.payload["text"],
                "metadata": {k: v for k, v in hit.payload.items() 
                           if k not in ["object_id", "text"]}
            }
            for hit in search_result
        ]
```

### Usage

```python
# After OpenMetadata ingestion
embeddings = generate_embeddings_from_minimal_schema(minimal_schema)

# Store in Qdrant
vector_store = QdrantVectorStore()
vector_store.create_collection()
vector_store.insert_embeddings(embeddings)
```

---

## Step 5: Search API Implementation

```python
from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

# Initialize services
embedding_generator = EmbeddingGenerator()
vector_store = QdrantVectorStore()

class SearchRequest(BaseModel):
    query: str
    limit: int = 10
    types: Optional[List[str]] = None  # Filter by type
    tags: Optional[List[str]] = None    # Filter by tags

class SearchResult(BaseModel):
    id: str
    score: float
    text: str
    type: str
    metadata: dict

@app.post("/api/v1/metadata/search", response_model=List[SearchResult])
async def search_metadata(request: SearchRequest):
    """
    Semantic search over metadata
    
    Example queries:
    - "customer email address"
    - "revenue and sales data"
    - "PII fields"
    - "fact tables in sales domain"
    """
    # Generate query embedding
    query_embedding = embedding_generator.generate_single_embedding(request.query)
    
    # Build filters
    filters = {}
    if request.types:
        filters["type"] = {"$in": request.types}
    if request.tags:
        filters["tags"] = {"$in": request.tags}
    
    # Search
    results = vector_store.search(
        query_embedding,
        limit=request.limit,
        filters=filters if filters else None
    )
    
    return [
        SearchResult(
            id=result["id"],
            score=result["score"],
            text=result["text"],
            type=result["metadata"]["type"],
            metadata=result["metadata"]
        )
        for result in results
    ]


@app.get("/api/v1/metadata/similar/{object_id}")
async def find_similar(object_id: str, limit: int = 5):
    """
    Find similar metadata objects
    
    Args:
        object_id: ID of metadata object (e.g., "entity:orders")
        limit: Number of similar items to return
    """
    # Get object embedding
    # (You'd need to store this mapping or retrieve from vector store)
    object_embedding = get_embedding_by_id(object_id)
    
    # Find similar
    results = vector_store.search(object_embedding, limit=limit + 1)
    
    # Filter out the object itself
    results = [r for r in results if r["id"] != object_id][:limit]
    
    return results
```

---

## Step 6: Integration with Data Pipeline

### Complete Flow

```python
def complete_metadata_ingestion_with_rag(job_id: str, minimal_schema: Dict[str, Any]):
    """
    Complete metadata ingestion flow including RAG embeddings
    
    Args:
        job_id: Job identifier
        minimal_schema: Output from Context Agent
    """
    
    # Step 1: Ingest to OpenMetadata (creates tables, columns, glossaries)
    print("Step 1: Ingesting to OpenMetadata...")
    openmetadata_result = ingest_to_openmetadata_complete(job_id, minimal_schema)
    
    # Step 2: Generate embeddings from descriptions
    print("Step 2: Generating RAG embeddings...")
    embeddings = generate_embeddings_from_minimal_schema(minimal_schema)
    
    # Step 3: Store in vector database
    print("Step 3: Storing embeddings in vector database...")
    vector_store = QdrantVectorStore()
    vector_store.insert_embeddings(embeddings)
    
    print(f"✓ Ingestion complete:")
    print(f"  - OpenMetadata: {openmetadata_result['tables_created']} tables, "
          f"{openmetadata_result['glossary_terms_created']} glossary terms")
    print(f"  - RAG: {len(embeddings)} embeddings generated")
    
    return {
        "openmetadata": openmetadata_result,
        "rag": {
            "embeddings_generated": len(embeddings),
            "vector_database": "Qdrant"
        }
    }
```

---

## Example Queries and Results

### Query 1: "customer email"

```python
query = "customer email"
results = search_metadata(SearchRequest(query=query, limit=3))

# Results:
[
    {
        "id": "column:customer.email",
        "score": 0.92,
        "text": "Column: Customer.Email Address | Type: varchar(255) | Description: Primary email address for customer communications...",
        "type": "column",
        "metadata": {"entity": "customer", "dataType": "VARCHAR"}
    },
    {
        "id": "column:orders.customer_email",
        "score": 0.88,
        "text": "Column: Orders.Customer Email Address | Type: varchar(255) | Description: Stores the customer's email address for communication...",
        "type": "column"
    },
    {
        "id": "term:Customer",
        "score": 0.75,
        "text": "Term: Customer | Domain: Sales & Billing | Description: An individual or organization...",
        "type": "glossary_term"
    }
]
```

### Query 2: "revenue and sales metrics"

```python
query = "revenue and sales metrics"
results = search_metadata(SearchRequest(query=query, limit=3))

# Results:
[
    {
        "id": "column:orders.amount",
        "score": 0.89,
        "text": "Column: Orders.Order Amount | Type: decimal(18,2) | Description: Represents the total monetary value... classified as Finance.Revenue...",
        "type": "column"
    },
    {
        "id": "entity:orders",
        "score": 0.85,
        "text": "Table: Orders | Type: Fact | Description: The Orders table serves as the central fact table for sales transactions...",
        "type": "entity"
    },
    {
        "id": "term:Revenue",
        "score": 0.82,
        "text": "Term: Revenue | Domain: Sales & Billing | Description: Income generated from sales...",
        "type": "glossary_term"
    }
]
```

### Query 3: "PII sensitive data"

```python
query = "PII sensitive data"
results = search_metadata(SearchRequest(query=query, types=["column"], limit=5))

# Results: All columns with PII.Sensitive tags
[
    {"id": "column:customer.email", "score": 0.91, "type": "column"},
    {"id": "column:customer.phone", "score": 0.88, "type": "column"},
    {"id": "column:customer.address", "score": 0.86, "type": "column"},
    ...
]
```

---

## Performance Considerations

### 1. Batch Embedding Generation
```python
# Instead of one-by-one
for text in texts:
    embedding = model.encode([text])[0]

# Batch process (much faster)
embeddings = model.encode(texts, batch_size=32)
```

### 2. Embedding Caching
```python
# Cache embeddings to avoid regeneration
import pickle

# Save
with open(f"embeddings_{job_id}.pkl", "wb") as f:
    pickle.dump(embeddings, f)

# Load
with open(f"embeddings_{job_id}.pkl", "rb") as f:
    embeddings = pickle.load(f)
```

### 3. Incremental Updates
```python
# When schema changes, only re-embed modified objects
def update_embeddings(modified_objects: List[str]):
    """Update embeddings for specific objects only"""
    for object_id in modified_objects:
        # Regenerate embedding
        new_embedding = generate_embedding_for_object(object_id)
        
        # Update in vector store
        vector_store.update_embedding(object_id, new_embedding)
```

---

## Monitoring and Metrics

```python
# Track RAG performance
{
    "embeddings_generated": 150,
    "generation_time_seconds": 2.5,
    "vector_db_insertion_time": 0.8,
    "avg_query_time_ms": 45,
    "total_queries": 1234,
    "avg_relevance_score": 0.82
}
```

---

## Next Steps

1. **Implement embedding generation** in data-pipeline service
2. **Set up Qdrant** (or alternative vector DB)
3. **Create search API** endpoint
4. **Integrate with frontend** for metadata search
5. **Add filters** for advanced search (by domain, type, tags)
6. **Monitor performance** and tune relevance

---

## Summary

- **Context Agent provides rich descriptions** → Perfect for semantic search
- **Generate embeddings** using sentence-transformers (same model as other agents)
- **Store in vector DB** with metadata for filtering
- **Search API** enables natural language queries
- **Integration is straightforward** - happens after OpenMetadata ingestion
- **Performance is excellent** - sub-50ms query times with proper setup

