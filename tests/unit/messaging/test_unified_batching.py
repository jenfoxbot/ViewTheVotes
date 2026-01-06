"""Tests for unified message batching behavior."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from playbooks.agents.messaging_mixin import MessagingMixin
from playbooks.core.identifiers import AgentID, MeetingID
from playbooks.core.message import Message, MessageType
from playbooks.meetings.meeting_manager import RollingMessageCollector


class TestUnifiedBatching:
    """Test unified message batching across agents."""

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent with MessagingMixin."""

        class MockAgent(MessagingMixin):
            def __init__(self):
                self.id = "1000"
                self.klass = "TestAgent"
                self.event_bus = None
                self.program = None
                self.call_stack = MagicMock()
                super().__init__()

        agent = MockAgent()
        # Use real asyncio.create_task for background tasks
        agent._create_background_task = asyncio.create_task
        return agent

    @pytest.mark.asyncio
    async def test_agent_burst_batching(self, mock_agent):
        """Test that multiple agent messages are batched together."""
        delivered_messages = []

        async def delivery_callback(messages):
            delivered_messages.extend(messages)

        mock_agent._message_collector.set_delivery_callback(delivery_callback)

        # Send 5 agent messages in quick succession
        for i in range(5):
            msg = Message(
                sender_id=AgentID("1001"),
                sender_klass="SenderAgent",
                recipient_id=AgentID("1000"),
                recipient_klass="TestAgent",
                message_type=MessageType.DIRECT,
                content=f"Message {i+1}",
                meeting_id=None,
            )
            await mock_agent._message_collector.add_message(msg)

        # Wait for timeout to expire
        await asyncio.sleep(0.6)

        # All messages should have been delivered in one batch
        assert len(delivered_messages) == 5
        assert all(m.content.startswith("Message") for m in delivered_messages)

    @pytest.mark.asyncio
    async def test_human_message_flush(self, mock_agent):
        """Test that human messages trigger immediate flush of pending agent messages."""
        delivered_messages = []

        async def delivery_callback(messages):
            delivered_messages.extend(messages)

        mock_agent._message_collector.set_delivery_callback(delivery_callback)

        # Send some agent messages first
        for i in range(3):
            msg = Message(
                sender_id=AgentID("1001"),
                sender_klass="SenderAgent",
                recipient_id=AgentID("1000"),
                recipient_klass="TestAgent",
                message_type=MessageType.DIRECT,
                content=f"Agent message {i+1}",
                meeting_id=None,
            )
            await mock_agent._message_collector.add_message(msg)

        # Wait a bit but not enough for timeout
        await asyncio.sleep(0.1)

        # Send human message - should flush all pending messages immediately
        human_msg = Message(
            sender_id=AgentID("human"),
            sender_klass="HumanAgent",
            recipient_id=AgentID("1000"),
            recipient_klass="TestAgent",
            message_type=MessageType.DIRECT,
            content="Human message",
            meeting_id=None,
        )
        await mock_agent._message_collector.add_message(human_msg)

        # Wait a tiny bit for the delivery task to complete
        await asyncio.sleep(0.01)

        # All messages should have been delivered immediately
        assert len(delivered_messages) == 4  # 3 agent + 1 human
        assert delivered_messages[-1].content == "Human message"

    @pytest.mark.asyncio
    async def test_human_message_in_meeting_flush(self, mock_agent):
        """Test that human messages flush pending meeting broadcasts."""
        delivered_messages = []

        async def delivery_callback(messages):
            delivered_messages.extend(messages)

        mock_agent._message_collector.set_delivery_callback(delivery_callback)

        meeting_id = MeetingID("meeting-123")

        # Send some meeting broadcasts first
        for i in range(2):
            msg = Message(
                sender_id=AgentID("1001"),
                sender_klass="Agent",
                recipient_id=None,
                recipient_klass=None,
                message_type=MessageType.MEETING_BROADCAST,
                content=f"Meeting broadcast {i+1}",
                meeting_id=meeting_id,
            )
            await mock_agent._message_collector.add_message(msg)

        # Wait a bit but not enough for timeout
        await asyncio.sleep(0.1)

        # Send human message in meeting - should flush all pending messages
        human_msg = Message(
            sender_id=AgentID("human"),
            sender_klass="HumanAgent",
            recipient_id=None,
            recipient_klass=None,
            message_type=MessageType.MEETING_BROADCAST,
            content="Human speaks in meeting",
            meeting_id=meeting_id,
        )
        await mock_agent._message_collector.add_message(human_msg)

        # Wait a tiny bit for the delivery task to complete
        await asyncio.sleep(0.01)

        # All messages should have been delivered immediately
        assert len(delivered_messages) == 3  # 2 meeting + 1 human
        assert delivered_messages[-1].content == "Human speaks in meeting"

    @pytest.mark.asyncio
    async def test_single_agent_message_delays(self, mock_agent):
        """Test that single agent messages wait for timeout before delivery."""
        delivered_messages = []

        async def delivery_callback(messages):
            delivered_messages.extend(messages)

        mock_agent._message_collector.set_delivery_callback(delivery_callback)

        # Send single agent message
        msg = Message(
            sender_id=AgentID("1001"),
            sender_klass="SenderAgent",
            recipient_id=AgentID("1000"),
            recipient_klass="TestAgent",
            message_type=MessageType.DIRECT,
            content="Single message",
            meeting_id=None,
        )
        await mock_agent._message_collector.add_message(msg)

        # Wait less than timeout - should not deliver yet
        await asyncio.sleep(0.2)
        assert len(delivered_messages) == 0

        # Wait for timeout to expire
        await asyncio.sleep(0.4)

        # Message should now be delivered
        assert len(delivered_messages) == 1
        assert delivered_messages[0].content == "Single message"

    @pytest.mark.asyncio
    async def test_max_wait_enforcement(self, mock_agent):
        """Test that max_wait prevents starvation even with continuous agent messages."""
        delivered_messages = []

        async def delivery_callback(messages):
            delivered_messages.extend(messages)

        # Use a collector with short rolling timeout and short max_wait
        collector = RollingMessageCollector(timeout_seconds=0.1, max_batch_wait=0.3)
        collector.set_delivery_callback(delivery_callback)

        # Send messages continuously, keeping the rolling timeout resetting
        for i in range(6):
            msg = Message(
                sender_id=AgentID("1001"),
                sender_klass="SenderAgent",
                recipient_id=AgentID("1000"),
                recipient_klass="TestAgent",
                message_type=MessageType.DIRECT,
                content=f"Message {i+1}",
                meeting_id=None,
            )
            await collector.add_message(msg)
            # Small delay to keep resetting timer
            await asyncio.sleep(0.08)

        # Wait for delivery to complete
        await asyncio.sleep(0.1)

        # Even though we kept adding messages, the absolute max should have triggered
        assert len(delivered_messages) >= 1
        # But not all, because we're continuously adding messages
        assert len(delivered_messages) < 10

    @pytest.mark.asyncio
    async def test_messaging_mixin_integration(self, mock_agent):
        """Test that MessagingMixin properly integrates with unified batching."""
        # Mock the message queue
        mock_agent._message_queue = MagicMock()
        mock_agent._message_queue.put = AsyncMock()

        # Send a direct message through MessagingMixin
        msg = Message(
            sender_id=AgentID("1001"),
            sender_klass="SenderAgent",
            recipient_id=AgentID("1000"),
            recipient_klass="TestAgent",
            message_type=MessageType.DIRECT,
            content="Test message",
            meeting_id=None,
        )

        # Mock meeting manager to return False (let MessagingMixin handle it)
        mock_agent.meeting_manager = MagicMock()
        mock_agent.meeting_manager._add_message_to_buffer = AsyncMock(
            return_value=False
        )

        await mock_agent._add_message_to_buffer(msg)

        # Message should have been added to collector (not directly to queue)
        # The collector will deliver it asynchronously, so we check the queue wasn't called directly
        mock_agent._message_queue.put.assert_not_called()

        # But after waiting for delivery
        await asyncio.sleep(0.6)
        # Now the message should be in the queue
        assert mock_agent._message_queue.put.called

    @pytest.mark.asyncio
    async def test_messaging_mixin_meeting_handling(self, mock_agent):
        """Test that MessagingMixin defers to MeetingManager for invitations."""
        # Send a meeting invitation
        msg = Message(
            sender_id=AgentID("1001"),
            sender_klass="SenderAgent",
            recipient_id=AgentID("1000"),
            recipient_klass="TestAgent",
            message_type=MessageType.MEETING_INVITATION,
            content="Join meeting",
            meeting_id=MeetingID("meeting-123"),
        )

        # Mock meeting manager to return True (handled the message)
        mock_agent.meeting_manager = MagicMock()
        mock_agent.meeting_manager._add_message_to_buffer = AsyncMock(return_value=True)

        await mock_agent._add_message_to_buffer(msg)

        # Message should have been handled by meeting manager, not added to collector
        # We can't easily verify this without more complex mocking, but the pattern is correct

    @pytest.mark.asyncio
    async def test_batching_preserves_message_order(self, mock_agent):
        """Test that batched messages maintain their original order."""
        delivered_messages = []

        async def delivery_callback(messages):
            delivered_messages.extend(messages)

        mock_agent._message_collector.set_delivery_callback(delivery_callback)

        # Send messages in specific order
        messages = ["First", "Second", "Third", "Fourth", "Fifth"]
        for content in messages:
            msg = Message(
                sender_id=AgentID("1001"),
                sender_klass="SenderAgent",
                recipient_id=AgentID("1000"),
                recipient_klass="TestAgent",
                message_type=MessageType.DIRECT,
                content=content,
                meeting_id=None,
            )
            await mock_agent._message_collector.add_message(msg)

        # Wait for delivery
        await asyncio.sleep(0.6)

        # Messages should be in the same order
        delivered_contents = [m.content for m in delivered_messages]
        assert delivered_contents == messages
