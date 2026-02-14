REPORT_FUNCTIONS = [
    {
        "name": "extract_section",
        "description": "Extracts exact text from a named section of the uploaded medical document",
        "parameters": {
            "type": "object",
            "properties": {
                "section_name": {
                    "type": "string",
                    "description": "Exact section name to extract"
                }
            },
            "required": ["section_name"]
        }
    },
    {
        "name": "extract_tables",
        "description": "Extracts all tables from the document",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "extract_figures",
        "description": "Extracts all clinical figures from the document",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "summarize_section",
        "description": "Summarizes a previously extracted section",
        "parameters": {
            "type": "object",
            "properties": {
                "source_section": {"type": "string"}
            },
            "required": ["source_section"]
        }
    }
]
