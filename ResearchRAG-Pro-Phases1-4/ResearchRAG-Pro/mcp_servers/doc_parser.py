#!/usr/bin/env python3
"""
Document Parser MCP Server
Handles PDF parsing with multimodal content extraction (text, equations, tables, algorithms)
Uses MinerU/Docling backend with LayoutLMv3 layout detection
"""

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, List, Dict, Optional
from dataclasses import dataclass, asdict

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("doc-parser")

# Initialize MCP server
app = Server("doc-parser")

@dataclass
class ContentChunk:
    """Structured content chunk from document parsing"""
    chunk_id: str
    type: str  # text|equation|table|algorithm|figure
    content: str
    latex: Optional[str] = None
    markdown: Optional[str] = None
    section: Optional[str] = None
    page: int = 0
    paper_id: Optional[str] = None
    bbox: Optional[List[float]] = None
    surrounding_text: Optional[str] = None
    confidence: float = 1.0
    metadata: Optional[Dict] = None


class DocumentParser:
    """Production document parser with MinerU/Docling backend"""
    
    def __init__(self):
        self.mineru_api_key = os.getenv("MINERU_API_KEY", "")
        self.layoutlm_path = os.getenv("LAYOUTLM_MODEL_PATH", "")
        self.max_workers = int(os.getenv("MAX_WORKERS", "4"))
        logger.info(f"DocumentParser initialized with {self.max_workers} workers")
    
    async def parse_pdf(self, pdf_path: str, paper_id: Optional[str] = None) -> List[ContentChunk]:
        """
        Parse PDF and extract all content types
        
        Args:
            pdf_path: Path to PDF file
            paper_id: Optional paper identifier
            
        Returns:
            List of ContentChunk objects
        """
        if not Path(pdf_path).exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        if not paper_id:
            paper_id = str(uuid.uuid4())
        
        logger.info(f"Parsing PDF: {pdf_path} (paper_id={paper_id})")
        
        # Simulate parsing (replace with actual MinerU/Docling integration)
        chunks = await self._parse_with_layout_detection(pdf_path, paper_id)
        
        logger.info(f"Extracted {len(chunks)} chunks from {pdf_path}")
        return chunks
    
    async def _parse_with_layout_detection(
        self, 
        pdf_path: str, 
        paper_id: str
    ) -> List[ContentChunk]:
        """Run layout detection and content extraction"""
        
        chunks = []
        
        # PHASE 1: Layout Detection with LayoutLMv3
        # TODO: Integrate actual LayoutLMv3 model
        layout_regions = await self._detect_layout(pdf_path)
        
        # PHASE 2: Content extraction by type
        for region in layout_regions:
            chunk = await self._extract_region(region, paper_id)
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    async def _detect_layout(self, pdf_path: str) -> List[Dict]:
        """Detect layout regions using LayoutLMv3"""
        # Placeholder - integrate with actual model
        # Returns list of regions with bbox, type, confidence
        
        return [
            {
                "type": "text",
                "bbox": [100, 100, 500, 200],
                "page": 1,
                "confidence": 0.95,
                "text": "Introduction\n\nThis paper presents a novel approach to..."
            },
            {
                "type": "equation",
                "bbox": [150, 250, 450, 300],
                "page": 1,
                "confidence": 0.92,
                "latex": "E = mc^2",
                "equation_number": "1"
            },
            {
                "type": "table",
                "bbox": [100, 350, 500, 500],
                "page": 1,
                "confidence": 0.88,
                "caption": "Experimental Results",
                "rows": [
                    ["Method", "Accuracy", "Time (s)"],
                    ["Baseline", "0.85", "120"],
                    ["Ours", "0.92", "95"]
                ]
            },
            {
                "type": "algorithm",
                "bbox": [100, 550, 500, 700],
                "page": 1,
                "confidence": 0.90,
                "pseudocode": "Algorithm 1: Fast Matrix Multiply\nInput: A, B\nOutput: C = A × B\n1: if n = 1 then\n2:   return A × B\n3: else\n4:   divide A, B into quadrants\n5:   return recursive_multiply(A, B)"
            }
        ]
    
    async def _extract_region(self, region: Dict, paper_id: str) -> Optional[ContentChunk]:
        """Extract content from a detected region"""
        
        region_type = region["type"]
        chunk_id = str(uuid.uuid4())
        
        if region_type == "equation":
            return await self._extract_equation(region, paper_id, chunk_id)
        elif region_type == "table":
            return await self._extract_table(region, paper_id, chunk_id)
        elif region_type == "algorithm":
            return await self._extract_algorithm(region, paper_id, chunk_id)
        elif region_type == "text":
            return await self._extract_text(region, paper_id, chunk_id)
        
        return None
    
    async def _extract_equation(
        self, 
        region: Dict, 
        paper_id: str, 
        chunk_id: str
    ) -> ContentChunk:
        """Extract equation with LaTeX preservation"""
        
        latex = region.get("latex", "")
        
        # Normalize LaTeX (remove unnecessary braces, standardize commands)
        normalized_latex = self._normalize_latex(latex)
        
        return ContentChunk(
            chunk_id=chunk_id,
            type="equation",
            content=normalized_latex,
            latex=normalized_latex,
            section=region.get("section"),
            page=region.get("page", 0),
            paper_id=paper_id,
            bbox=region.get("bbox"),
            confidence=region.get("confidence", 1.0),
            metadata={
                "equation_number": region.get("equation_number"),
                "is_inline": region.get("is_inline", False)
            }
        )
    
    async def _extract_table(
        self, 
        region: Dict, 
        paper_id: str, 
        chunk_id: str
    ) -> ContentChunk:
        """Extract table with structure preservation"""
        
        rows = region.get("rows", [])
        
        # Convert to Markdown
        markdown_table = self._to_markdown_table(rows)
        
        # Extract column statistics
        col_stats = self._compute_column_stats(rows)
        
        return ContentChunk(
            chunk_id=chunk_id,
            type="table",
            content=markdown_table,
            markdown=markdown_table,
            section=region.get("section"),
            page=region.get("page", 0),
            paper_id=paper_id,
            bbox=region.get("bbox"),
            confidence=region.get("confidence", 1.0),
            metadata={
                "caption": region.get("caption", ""),
                "column_stats": col_stats,
                "num_rows": len(rows),
                "num_cols": len(rows[0]) if rows else 0
            }
        )
    
    async def _extract_algorithm(
        self, 
        region: Dict, 
        paper_id: str, 
        chunk_id: str
    ) -> ContentChunk:
        """Extract algorithm pseudocode"""
        
        pseudocode = region.get("pseudocode", "")
        
        # Generate description
        description = self._generate_algorithm_description(pseudocode)
        
        return ContentChunk(
            chunk_id=chunk_id,
            type="algorithm",
            content=pseudocode,
            section=region.get("section"),
            page=region.get("page", 0),
            paper_id=paper_id,
            bbox=region.get("bbox"),
            confidence=region.get("confidence", 1.0),
            metadata={
                "algorithm_name": region.get("name", "Algorithm"),
                "line_count": len(pseudocode.split('\n')),
                "description": description,
                "complexity": region.get("complexity")
            }
        )
    
    async def _extract_text(
        self, 
        region: Dict, 
        paper_id: str, 
        chunk_id: str
    ) -> ContentChunk:
        """Extract text passage"""
        
        text = region.get("text", "")
        
        return ContentChunk(
            chunk_id=chunk_id,
            type="text",
            content=text,
            section=region.get("section"),
            page=region.get("page", 0),
            paper_id=paper_id,
            bbox=region.get("bbox"),
            confidence=region.get("confidence", 1.0),
            metadata={}
        )
    
    def _normalize_latex(self, latex: str) -> str:
        """Normalize LaTeX syntax"""
        # Remove unnecessary braces
        normalized = latex.replace("{ ", "{").replace(" }", "}")
        # Standardize commands
        normalized = normalized.replace("\\tfrac", "\\frac")
        normalized = normalized.replace("\\dfrac", "\\frac")
        return normalized
    
    def _to_markdown_table(self, rows: List[List[str]]) -> str:
        """Convert rows to Markdown table"""
        if not rows:
            return ""
        
        # Header row
        markdown = "| " + " | ".join(rows[0]) + " |\n"
        # Separator
        markdown += "| " + " | ".join(["---"] * len(rows[0])) + " |\n"
        # Data rows
        for row in rows[1:]:
            markdown += "| " + " | ".join(row) + " |\n"
        
        return markdown
    
    def _compute_column_stats(self, rows: List[List[str]]) -> Dict:
        """Compute statistics for numeric columns"""
        if len(rows) < 2:
            return {}
        
        stats = {}
        headers = rows[0]
        
        for col_idx, header in enumerate(headers):
            values = []
            for row in rows[1:]:
                try:
                    values.append(float(row[col_idx]))
                except (ValueError, IndexError):
                    continue
            
            if values:
                stats[header] = {
                    "min": min(values),
                    "max": max(values),
                    "mean": sum(values) / len(values)
                }
        
        return stats
    
    def _generate_algorithm_description(self, pseudocode: str) -> str:
        """Generate natural language description of algorithm"""
        lines = pseudocode.split('\n')
        if lines:
            # Extract algorithm name from first line
            first_line = lines[0]
            if ':' in first_line:
                return first_line.split(':')[1].strip()
        return "Algorithm pseudocode"
    
    async def extract_equations(self, pdf_path: str, page: int = -1) -> List[ContentChunk]:
        """Extract only equations from PDF"""
        all_chunks = await self.parse_pdf(pdf_path)
        equations = [c for c in all_chunks if c.type == "equation"]
        
        if page >= 0:
            equations = [e for e in equations if e.page == page]
        
        return equations
    
    async def extract_tables(self, pdf_path: str, page: int = -1) -> List[ContentChunk]:
        """Extract only tables from PDF"""
        all_chunks = await self.parse_pdf(pdf_path)
        tables = [c for c in all_chunks if c.type == "table"]
        
        if page >= 0:
            tables = [t for t in tables if t.page == page]
        
        return tables
    
    async def extract_algorithms(self, pdf_path: str, page: int = -1) -> List[ContentChunk]:
        """Extract only algorithms from PDF"""
        all_chunks = await self.parse_pdf(pdf_path)
        algorithms = [c for c in all_chunks if c.type == "algorithm"]
        
        if page >= 0:
            algorithms = [a for a in algorithms if a.page == page]
        
        return algorithms


# Global parser instance
parser = DocumentParser()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available document parsing tools"""
    return [
        Tool(
            name="parse_pdf",
            description="Parse a PDF and extract all content types (text, equations, tables, algorithms)",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": "Path to the PDF file to parse"
                    },
                    "paper_id": {
                        "type": "string",
                        "description": "Optional paper identifier (UUID generated if not provided)"
                    }
                },
                "required": ["pdf_path"]
            }
        ),
        Tool(
            name="extract_equations",
            description="Extract only equations from a PDF document",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": "Path to the PDF file"
                    },
                    "page": {
                        "type": "number",
                        "description": "Optional: extract from specific page (-1 for all pages)",
                        "default": -1
                    }
                },
                "required": ["pdf_path"]
            }
        ),
        Tool(
            name="extract_tables",
            description="Extract only tables from a PDF document",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": "Path to the PDF file"
                    },
                    "page": {
                        "type": "number",
                        "description": "Optional: extract from specific page (-1 for all pages)",
                        "default": -1
                    }
                },
                "required": ["pdf_path"]
            }
        ),
        Tool(
            name="extract_algorithms",
            description="Extract only algorithms/pseudocode from a PDF document",
            inputSchema={
                "type": "object",
                "properties": {
                    "pdf_path": {
                        "type": "string",
                        "description": "Path to the PDF file"
                    },
                    "page": {
                        "type": "number",
                        "description": "Optional: extract from specific page (-1 for all pages)",
                        "default": -1
                    }
                },
                "required": ["pdf_path"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    
    try:
        if name == "parse_pdf":
            pdf_path = arguments["pdf_path"]
            paper_id = arguments.get("paper_id")
            
            chunks = await parser.parse_pdf(pdf_path, paper_id)
            
            # Convert chunks to dict for JSON serialization
            result = {
                "paper_id": chunks[0].paper_id if chunks else None,
                "total_chunks": len(chunks),
                "chunks": [asdict(chunk) for chunk in chunks]
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "extract_equations":
            pdf_path = arguments["pdf_path"]
            page = arguments.get("page", -1)
            
            equations = await parser.extract_equations(pdf_path, page)
            
            result = {
                "total_equations": len(equations),
                "equations": [asdict(eq) for eq in equations]
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "extract_tables":
            pdf_path = arguments["pdf_path"]
            page = arguments.get("page", -1)
            
            tables = await parser.extract_tables(pdf_path, page)
            
            result = {
                "total_tables": len(tables),
                "tables": [asdict(table) for table in tables]
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        elif name == "extract_algorithms":
            pdf_path = arguments["pdf_path"]
            page = arguments.get("page", -1)
            
            algorithms = await parser.extract_algorithms(pdf_path, page)
            
            result = {
                "total_algorithms": len(algorithms),
                "algorithms": [asdict(alg) for alg in algorithms]
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
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
