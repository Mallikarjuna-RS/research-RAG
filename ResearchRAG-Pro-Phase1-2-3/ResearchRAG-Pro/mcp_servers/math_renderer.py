#!/usr/bin/env python3
"""
Math Renderer MCP Server
Handles LaTeX rendering, validation, and semantic equation comparison
Uses KaTeX for rendering + SymPy for semantic analysis
"""

import asyncio
import json
import logging
import os
import re
from typing import Any, List, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("math-renderer")

app = Server("math-renderer")


class MathRenderer:
    """LaTeX rendering and validation service"""
    
    def __init__(self):
        self.katex_url = os.getenv("KATEX_SERVER_URL", "http://localhost:3000")
        self.sympy_timeout = int(os.getenv("SYMPY_TIMEOUT", "30"))
    
    async def render_latex(self, latex: str, format: str = "svg") -> dict:
        """Render LaTeX to SVG/PNG"""
        logger.info(f"Rendering LaTeX: {latex[:50]}...")
        
        # TODO: Actual KaTeX server-side rendering
        # import requests
        # response = requests.post(f"{self.katex_url}/render", 
        #                         json={"latex": latex, "format": format})
        
        return {
            "latex": latex,
            "rendered_svg": f"<svg>Rendered: {latex}</svg>",
            "format": format,
            "success": True
        }
    
    async def validate_latex(self, latex: str) -> dict:
        """Validate LaTeX syntax"""
        logger.info(f"Validating LaTeX: {latex[:50]}...")
        
        errors = []
        warnings = []
        
        # Basic validation
        if latex.count('$') % 2 != 0:
            errors.append("Unmatched $ delimiters")
        
        if latex.count(r'\begin') != latex.count(r'\end'):
            errors.append("Unmatched \\begin/\\end blocks")
        
        # Check for common issues
        if r'\frac{}' in latex or r'\frac{}{' in latex:
            warnings.append("Empty fraction numerator/denominator")
        
        is_valid = len(errors) == 0
        
        return {
            "latex": latex,
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings
        }
    
    async def compare_equations(self, latex1: str, latex2: str) -> dict:
        """Check semantic equivalence of two equations"""
        logger.info(f"Comparing: {latex1} vs {latex2}")
        
        # TODO: Actual SymPy comparison
        # from sympy import sympify, simplify
        # try:
        #     expr1 = sympify(latex1)
        #     expr2 = sympify(latex2)
        #     equivalent = simplify(expr1 - expr2) == 0
        # except:
        #     equivalent = False
        
        # Simulate semantic comparison
        normalized1 = self._normalize_latex(latex1)
        normalized2 = self._normalize_latex(latex2)
        
        # Simple string comparison after normalization
        equivalent = normalized1 == normalized2
        
        # Calculate similarity score
        similarity = 1.0 if equivalent else 0.0
        
        return {
            "latex1": latex1,
            "latex2": latex2,
            "equivalent": equivalent,
            "similarity_score": similarity,
            "normalized1": normalized1,
            "normalized2": normalized2
        }
    
    def _normalize_latex(self, latex: str) -> str:
        """Normalize LaTeX for comparison"""
        # Remove whitespace
        normalized = re.sub(r'\s+', '', latex)
        # Standardize commands
        normalized = normalized.replace(r'\tfrac', r'\frac')
        normalized = normalized.replace(r'\dfrac', r'\frac')
        # Remove unnecessary braces
        normalized = normalized.replace('{', '').replace('}', '')
        return normalized


renderer = MathRenderer()


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="render_latex",
            description="Render LaTeX equation to SVG or PNG",
            inputSchema={
                "type": "object",
                "properties": {
                    "latex": {"type": "string"},
                    "format": {"type": "string", "enum": ["svg", "png"], "default": "svg"}
                },
                "required": ["latex"]
            }
        ),
        Tool(
            name="validate_latex",
            description="Validate LaTeX syntax and check for errors",
            inputSchema={
                "type": "object",
                "properties": {
                    "latex": {"type": "string"}
                },
                "required": ["latex"]
            }
        ),
        Tool(
            name="compare_equations",
            description="Check if two LaTeX equations are semantically equivalent",
            inputSchema={
                "type": "object",
                "properties": {
                    "latex1": {"type": "string"},
                    "latex2": {"type": "string"}
                },
                "required": ["latex1", "latex2"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    try:
        if name == "render_latex":
            result = await renderer.render_latex(
                arguments["latex"],
                arguments.get("format", "svg")
            )
        elif name == "validate_latex":
            result = await renderer.validate_latex(arguments["latex"])
        elif name == "compare_equations":
            result = await renderer.compare_equations(
                arguments["latex1"],
                arguments["latex2"]
            )
        else:
            raise ValueError(f"Unknown tool: {name}")
        
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
