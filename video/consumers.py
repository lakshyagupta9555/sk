import json
from collections import defaultdict
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import VideoCall

class VideoCallConsumer(AsyncWebsocketConsumer):
    active_participants = defaultdict(lambda: defaultdict(set))

    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close()
            return

        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'video_{self.room_id}'
        self.username = self.scope['user'].username

        participants = self.active_participants[self.room_group_name]
        participants[self.username].add(self.channel_name)
        participant_count = len(participants)

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'room_state',
            'participant_count': participant_count,
        }))

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'participant_joined',
                'sender': self.username,
                'participant_count': participant_count,
            }
        )

    async def disconnect(self, close_code):
        participant_count = None
        if hasattr(self, 'room_group_name'):
            participants = self.active_participants.get(self.room_group_name)
            if participants is not None:
                user_channels = participants.get(self.username)
                if user_channels is not None:
                    user_channels.discard(self.channel_name)
                    if not user_channels:
                        participants.pop(self.username, None)

                participant_count = len(participants)
                if participant_count == 0:
                    self.active_participants.pop(self.room_group_name, None)

        if hasattr(self, 'room_group_name'):
            await self.finalize_call_on_disconnect(participant_count)
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

        if hasattr(self, 'username'):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'participant_left',
                    'sender': self.username,
                    'participant_count': participant_count,
                }
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type in {'offer', 'answer', 'ice_candidate', 'end_call'}:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'webrtc_signal',
                    'signal_type': message_type,
                    'payload': data.get('payload'),
                    'sender': self.username,
                }
            )
            return
        
        # Handle whiteboard drawing events
        if message_type == 'whiteboard':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'whiteboard_draw',
                    'action': data.get('action'),
                    'tool': data.get('tool'),
                    'color': data.get('color'),
                    'size': data.get('size'),
                    'x': data.get('x'),
                    'y': data.get('y'),
                    'lastX': data.get('lastX'),
                    'lastY': data.get('lastY'),
                    'text': data.get('text'),
                    'sender': data.get('sender')
                }
            )
        elif message_type == 'whiteboard_clear':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'whiteboard_clear',
                    'sender': data.get('sender')
                }
            )

    async def whiteboard_draw(self, event):
        # Send whiteboard drawing data to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'whiteboard',
            'action': event.get('action'),
            'tool': event.get('tool'),
            'color': event.get('color'),
            'size': event.get('size'),
            'x': event.get('x'),
            'y': event.get('y'),
            'lastX': event.get('lastX'),
            'lastY': event.get('lastY'),
            'text': event.get('text'),
            'sender': event.get('sender')
        }))

    async def whiteboard_clear(self, event):
        # Send clear whiteboard command
        await self.send(text_data=json.dumps({
            'type': 'whiteboard_clear',
            'sender': event.get('sender')
        }))

    async def participant_joined(self, event):
        if event.get('sender') != getattr(self, 'username', None):
            await self.mark_call_active()

        await self.send(text_data=json.dumps({
            'type': 'participant_joined',
            'sender': event.get('sender'),
            'participant_count': event.get('participant_count')
        }))

    async def participant_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'participant_left',
            'sender': event.get('sender'),
            'participant_count': event.get('participant_count')
        }))

    async def webrtc_signal(self, event):
        if event.get('sender') == getattr(self, 'username', None):
            return

        await self.send(text_data=json.dumps({
            'type': event.get('signal_type'),
            'payload': event.get('payload'),
            'sender': event.get('sender')
        }))

    @database_sync_to_async
    def mark_call_active(self):
        VideoCall.objects.filter(
            room_id=self.room_id,
            status='calling'
        ).update(status='active')

    @database_sync_to_async
    def finalize_call_on_disconnect(self, participant_count):
        call = VideoCall.objects.filter(room_id=self.room_id).first()
        if not call or call.status == 'ended':
            return

        participants = self.active_participants.get(self.room_group_name, {})
        self_remaining = participants.get(self.username, set())
        if self_remaining:
            return

        if participant_count == 0 and call.status == 'calling':
            call.status = 'missed'
            call.ended_at = timezone.now()
        else:
            call.status = 'ended'
            call.ended_at = timezone.now()

        if call.started_at and call.ended_at:
            call.duration = int((call.ended_at - call.started_at).total_seconds())

        call.save(update_fields=['status', 'ended_at', 'duration'])
