
from channels.layers import get_channel_layer
from typing import Iterable

async def refresh_counts_for_groups(group_names: Iterable[str]) -> None:
    """
    Send an async group message that triggers each consumer's refresh_counts().
    You can pass in any number of group names.
    """
    channel_layer = get_channel_layer()
    for group in group_names:
        print(f"[refresh_counts] sending to group {group}")
        await channel_layer.group_send(
            group,
            {
                "type": "refresh_counts",
            }
        )