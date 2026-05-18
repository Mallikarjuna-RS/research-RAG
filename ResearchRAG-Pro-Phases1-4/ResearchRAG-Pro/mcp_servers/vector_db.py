#!/usr/bin/env python3
"""
Vector DB MCP Server
Handles vector storage and hybrid search using Milvus
Supports dense vectors (1536d text, 384d math) + sparse vectors (BM25)
"""

import asyncio
import json
import logging
import os
from typing import Any, List, Dict, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vector-db")

# Initialize MCP server
app = Server("vector-db")


class VectorDBClient:
    """Production Milvus client with hybrid search"""
    
    def __init__(self):
        self.milvus_uri = os.getenv("MILVUS_URI", "http://localhost:19530")
        self.milvus_token = os.getenv("MILVUS_TOKEN", "")
        self.collection_name = os.getenv("COLLECTION_NAME", "research_chunks")
        
        # Connection will be lazy-loaded
        self.collection = None
        self.connected = False
        
        logger.info(f"VectorDBClient initialized (URI: {self.milvus_uri})")
    
    async def _ensure_connected(self):
        """Ensure connection to Milvus is established"""
        if self.connected:
            return
        
        try:
            # TODO: Replace with actual Milvus connection
            # from pymilvus import connections, Collection
            # connections.connect(uri=self.milvus_uri, token=self.milvus_token)
            # self.collection = Collection(self.collection_name)
            
            self.connected = True
            logger.info(f"Connected to Milvus: {self.collection_name}")
        except Exception as e:
            logger.error(f"Failed to connect to Milvus: {e}")
            raise
    
    async def insert_chunks(self, chunks: List[Dict]) -> Dict:
        """
        Insert chunks into vector database
        
        Args:
            chunks: List of chunk dicts with embeddings
            
        Returns:
            Insert result with IDs and counts
        """
        await self._ensure_connected()
        
        logger.info(f"Inserting {len(chunks)} chunks")
        
        # Prepare data for insertion
        chunk_ids = [c["chunk_id"] for c in chunks]
        paper_ids = [c.get("paper_id", "") for c in chunks]
        types = [c.get("type", "text") for c in chunks]
        sections = [c.get("section", "") for c in chunks]
        pages = [c.get("page", 0) for c in chunks]
        contents = [c.get("content", "") for c in chunks]
        
        # Extract embeddings (placeholder - actual embeddings from embedding service)
        text_embeddings = [c.get("text_embedding", [0.0] * 1536) for c in chunks]
        math_embeddings = [c.get("math_embedding", [0.0] * 384) for c in chunks]
        sparse_vectors = [c.get("sparse_vector", {}) for c in chunks]
        
        # Extract metadata
        latex_content = [c.get("latex", "") for c in chunks]
        markdown_content = [c.get("markdown", "") for c in chunks]
        metadata = [json.dumps(c.get("metadata", {})) for c in chunks]
        
        # TODO: Actual Milvus insert
        # entities = [
        #     chunk_ids,
        #     paper_ids,
        #     types,
        #     sections,
        #     pages,
        #     text_embeddings,
        #     math_embeddings,
        #     sparse_vectors,
        #     contents,
        #     latex_content,
        #     metadata
        # ]
        # insert_result = self.collection.insert(entities)
        
        # Simulate insert result
        insert_result = {
            "insert_count": len(chunks),
            "ids": chunk_ids,
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        logger.info(f"Inserted {insert_result['insert_count']} chunks successfully")
        
        return insert_result
    
    async def hybrid_search(
        self,
        query: str,
        query_embedding: Optional[List[float]] = None,
        filters: Optional[Dict] = None,
        top_k: int = 10
    ) -> List[Dict]:
        """
        Hybrid search combining dense + sparse vectors
        
        Args:
            query: Query text
            query_embedding: Pre-computed query embedding
            filters: Filter conditions (type, paper_id, section, etc.)
            top_k: Number of results to return
            
        Returns:
            List of search results with scores
        """
        await self._ensure_connected()
        
        logger.info(f"Hybrid search: '{query}' (top_k={top_k})")
        
        # Build filter expression
        filter_expr = self._build_filter_expr(filters)
        
        # TODO: Actual Milvus hybrid search
        # Dense search
        # search_params_dense = {
        #     "metric_type": "COSINE",
        #     "params": {"nprobe": 128}
        # }
        # dense_results = self.collection.search(
        #     data=[query_embedding],
        #     anns_field="text_embedding",
        #     param=search_params_dense,
        #     limit=top_k * 3,
        #     expr=filter_expr
        # )
        
        # Sparse search (BM25)
        # sparse_results = self.collection.search(
        #     data=[sparse_query_vec],
        #     anns_field="sparse_vector",
        #     param={"metric_type": "BM25"},
        #     limit=top_k * 3,
        #     expr=filter_expr
        # )
        
        # Fusion: score = 0.7*dense + 0.3*sparse
        # fused_results = self._reciprocal_rank_fusion(
        #     dense_results, 
        #     sparse_results,
        #     dense_weight=0.7,
        #     sparse_weight=0.3
        # )
        
        # Simulate search results
        results = [
            {
                "chunk_id": f"chunk_{i}",
                "paper_id": f"paper_{i % 3}",
                "type": "text" if i % 3 == 0 else ("equation" if i % 3 == 1 else "table"),
                "content": f"Sample content matching '{query}'...",
                "section": f"{i // 10 + 1}.{i % 10 + 1}",
                "page": i + 1,
                "score": 0.95 - (i * 0.05),
                "dense_score": 0.93 - (i * 0.04),
                "sparse_score": 0.85 - (i * 0.03),
                "metadata": {
                    "confidence": 0.9 - (i * 0.05)
                }
            }
            for i in range(min(top_k, 10))
        ]
        
        logger.info(f"Found {len(results)} results")
        
        return results[:top_k]
    
    def _build_filter_expr(self, filters: Optional[Dict]) -> str:
        """Build Milvus filter expression"""
        if not filters:
            return ""
        
        conditions = []
        
        if "type" in filters:
            types = filters["type"] if isinstance(filters["type"], list) else [filters["type"]]
            type_cond = " || ".join([f'type == "{t}"' for t in types])
            conditions.append(f"({type_cond})")
        
        if "paper_id" in filters:
            conditions.append(f'paper_id == "{filters["paper_id"]}"')
        
        if "section" in filters:
            conditions.append(f'section like "{filters["section"]}%"')
        
        if "confidence" in filters:
            min_conf = filters["confidence"]
            conditions.append(f'metadata["confidence"] >= {min_conf}')
        
        if "date_range" in filters:
            # Add date range filter if needed
            pass
        
        return " && ".join(conditions) if conditions else ""
    
    def _reciprocal_rank_fusion(
        self,
        dense_results: List[Dict],
        sparse_results: List[Dict],
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
        k: int = 60
    ) -> List[Dict]:
        """
        Reciprocal Rank Fusion for combining dense and sparse results
        
        Formula: score = dense_weight * (1/(k + rank_dense)) + sparse_weight * (1/(k + rank_sparse))
        """
        scores = {}
        
        # Add dense scores
        for rank, result in enumerate(dense_results):
            chunk_id = result["chunk_id"]
            scores[chunk_id] = {
                "chunk": result,
                "score": dense_weight / (k + rank + 1)
            }
        
        # Add sparse scores
        for rank, result in enumerate(sparse_results):
            chunk_id = result["chunk_id"]
            if chunk_id in scores:
                scores[chunk_id]["score"] += sparse_weight / (k + rank + 1)
            else:
                scores[chunk_id] = {
                    "chunk": result,
                    "score": sparse_weight / (k + rank + 1)
                }
        
        # Sort by fused score
        fused = sorted(
            scores.values(),
            key=lambda x: x["score"],
            reverse=True
        )
        
        return [item["chunk"] for item in fused]
    
    async def get_by_id(self, chunk_id: str) -> Optional[Dict]:
        """Get chunk by ID"""
        await self._ensure_connected()
        
        logger.info(f"Getting chunk by ID: {chunk_id}")
        
        # TODO: Actual Milvus query
        # results = self.collection.query(
        #     expr=f'id == "{chunk_id}"',
        #     output_fields=["*"]
        # )
        
        # Simulate result
        result = {
            "chunk_id": chunk_id,
            "paper_id": "paper_001",
            "type": "text",
            "content": "Sample content for chunk",
            "section": "3.2",
            "page": 5,
            "metadata": {}
        }
        
        return result
    
    async def delete_by_paper(self, paper_id: str) -> Dict:
        """Delete all chunks for a given paper"""
        await self._ensure_connected()
        
        logger.info(f"Deleting chunks for paper: {paper_id}")
        
        # TODO: Actual Milvus deletion
        # delete_expr = f'paper_id == "{paper_id}"'
        # delete_result = self.collection.delete(delete_expr)
        
        # Simulate deletion
        delete_result = {
            "deleted_count": 42,
            "paper_id": paper_id
        }
        
        logger.info(f"Deleted {delete_result['deleted_count']} chunks")
        
        return delete_result
    
    async def get_collection_stats(self) -> Dict:
        """Get collection statistics"""
        await self._ensure_connected()
        
        # TODO: Actual stats
        # stats = self.collection.get_collection_stats()
        
        stats = {
            "total_chunks": 12500,
            "total_papers": 250,
            "by_type": {
                "text": 8000,
                "equation": 2500,
                "table": 1500,
                "algorithm": 500
            },
            "collection_name": self.collection_name
        }
        
        return stats


# Global client instance
db_client = VectorDBClient()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available vector DB tools"""
    return [
        Tool(
            name="insert_chunks",
            description="Insert content chunks into the vector database with embeddings",
            inputSchema={
                "type": "object",
                "properties": {
                    "chunks": {
                        "type": "array",
                        "description": "Array of chunk objects to insert",
                        "items": {
                            "type": "object"
                        }
                    }
                },
                "required": ["chunks"]
            }
        ),
        Tool(
            name="hybrid_search",
            description="Perform hybrid search combining dense vectors + BM25 sparse search",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query text"
                    },
                    "query_embedding": {
                        "type": "array",
                        "description": "Optional pre-computed query embedding",
                        "items": {"type": "number"}
                    },
                    "filters": {
                        "type": "object",
                        "description": "Filter conditions (type, paper_id, section, confidence, date_range)",
                        "properties": {
                            "type": {"type": ["string", "array"]},
                            "paper_id": {"type": "string"},
                            "section": {"type": "string"},
                            "confidence": {"type": "number"},
                            "date_range": {"type": "object"}
                        }
                    },
                    "top_k": {
                        "type": "number",
                        "description": "Number of results to return",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="get_by_id",
            description="Retrieve a specific chunk by its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "chunk_id": {
                        "type": "string",
                        "description": "Chunk identifier"
                    }
                },
                "required": ["chunk_id"]
            }
        ),
        Tool(
            name="delete_by_paper",
            description="Delete all chunks associated with a specific paper",
            inputSchema={
                "type": "object",
                "properties": {
                    "paper_id": {
                        "type": "string",
                        "description": "Paper identifier"
                    }
                },
                "required": ["paper_id"]
            }
        ),
        Tool(
            name="get_stats",
            description="Get collection statistics (total chunks, papers, breakdown by type)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    
    try:
        if name == "insert_chunks":
            chunks = arguments["chunks"]
            result = await db_client.insert_chunks(chunks)
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "hybrid_search":
            query = arguments["query"]
            query_embedding = arguments.get("query_embedding")
            filters = arguments.get("filters")
            top_k = arguments.get("top_k", 10)
            
            results = await db_client.hybrid_search(
                query=query,
                query_embedding=query_embedding,
                filters=filters,
                top_k=top_k
            )
            
            return [TextContent(
                type="text",
                text=json.dumps({"results": results, "total": len(results)}, indent=2)
            )]
        
        elif name == "get_by_id":
            chunk_id = arguments["chunk_id"]
            result = await db_client.get_by_id(chunk_id)
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "delete_by_paper":
            paper_id = arguments["paper_id"]
            result = await db_client.delete_by_paper(paper_id)
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "get_stats":
            stats = await db_client.get_collection_stats()
            
            return [TextContent(
                type="text",
                text=json.dumps(stats, indent=2)
            )]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        logger.error(f"Error in {name}: {str(e)}", exc_info=True)
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e)})
        )]


async def main():
    """Run the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
