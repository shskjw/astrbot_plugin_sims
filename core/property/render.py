"""Property (Real Estate) subsystem renderer."""

from typing import Dict, Any

class PropertyRenderer:
    """Renders property-related information."""

    def render_property_info(self, prop: Dict[str, Any]) -> str:
        """Render property information."""
        return f"【{prop.get('name', '未知房产')}】\n价格: {prop.get('price', 0)} 金币\n租金: {prop.get('rent', 0)} 金币/周"

    def render_property_list(self, properties: list) -> str:
        """Render a list of available properties."""
        if not properties:
            return "暂无房产"
        
        lines = ["【可购房产列表】"]
        for prop in properties:
            lines.append(f"{prop.get('id', 'N/A')} - {self.render_property_info(prop)}")
        return "\n".join(lines)

    def render_user_properties(self, user_id: str, properties: list) -> str:
        """Render user's properties."""
        if not properties:
            return f"用户 {user_id} 暂无房产"
        
        lines = [f"【{user_id} 的房产】"]
        total_rent = 0
        for prop in properties:
            rent = prop.get('rent', 0)
            total_rent += rent
            lines.append(f"{prop.get('name', '未知')} - 租金: {rent}")
        lines.append(f"总租金收入: {total_rent}")
        return "\n".join(lines)
