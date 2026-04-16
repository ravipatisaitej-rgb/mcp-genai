"""Example usage of MCP Tools"""
from config.settings import get_app_config
from tools import ConfluenceTool, AzureBoardsTool
from tools.manager import ToolManager, ToolType

def example_tool_manager():
    """Use tool manager for automatic routing"""
    print("\n=== Tool Manager Example ===")
    
    config = get_app_config()
    manager = ToolManager()
    
    if config.confluence:
        confluence = ConfluenceTool(
            config.confluence.url,
            config.confluence.username,
            config.confluence.api_token
        )
        manager.register_tool(ToolType.CONFLUENCE, confluence)
    
    print(f"Available tools: {manager.list_available_tools()}")
    
    result = manager.execute_query("Find documentation")
    print(f"Success: {result.success}")
    if result.success:
        print(f"Tool used: {result.metadata.get('tool_used')}")

def example_azure_boards():
    """Query Azure Boards"""
    print("\n=== Azure Boards Example ===")
    
    config = get_app_config()
    if not config.azure_boards:
        print("Azure Boards not configured")
        return
    
    tool = AzureBoardsTool(
        config.azure_boards.organization,
        config.azure_boards.project,
        config.azure_boards.pat_token
    )
    
    result = tool.execute("Show my open work items")
    print(f"Success: {result.success}")
    if result.success and result.data:
        print(f"Items found: {result.data.get('metrics', {}).get('total_items', 0)}")

if __name__ == "__main__":
    print("MCP Tools Examples")
    print("Configure environment variables before running")
    # Uncomment to run:
    # example_tool_manager()
    # example_azure_boards()
