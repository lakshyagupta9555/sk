from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import VideoCall, VideoCallRating
import uuid

@login_required
def video_call_list(request):
    calls = VideoCall.objects.filter(
        Q(caller=request.user) | Q(receiver=request.user)
    ).order_by('-started_at')[:20]

    rated_call_ids = set(
        VideoCallRating.objects.filter(rater=request.user).values_list('call_id', flat=True)
    )

    return render(
        request,
        'video/call_list.html',
        {
            'calls': calls,
            'rated_call_ids': rated_call_ids,
        },
    )

@login_required
def start_call(request, user_id):
    receiver = get_object_or_404(User, id=user_id)
    if receiver == request.user:
        return redirect('dashboard:home')

    room_id = str(uuid.uuid4())
    call = VideoCall.objects.create(
        caller=request.user,
        receiver=receiver,
        room_id=room_id,
        status='calling'
    )

    # Build the absolute room URL to send to receiver
    room_url = request.build_absolute_uri(
        reverse('video:video_room', kwargs={'room_id': room_id})
    )

    # Notify receiver in real-time via their notification WebSocket
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'notifications_{receiver.id}',
        {
            'type': 'incoming_call',
            'caller': request.user.username,
            'caller_id': request.user.id,
            'room_id': room_id,
            'room_url': room_url,
        }
    )

    return redirect('video:video_room', room_id=room_id)

@login_required
def video_room(request, room_id):
    call = get_object_or_404(VideoCall, room_id=room_id)

    # Check if user is participant
    if call.caller != request.user and call.receiver != request.user:
        return redirect('dashboard:home')

    # Don't allow joining ended calls
    if call.status == 'ended':
        return redirect('video:call_list')

    # Mark active only when the receiver joins (not just the caller alone)
    if call.status == 'calling' and call.receiver == request.user:
        call.status = 'active'
        call.save()

    context = {
        'call': call,
        'room_id': room_id,
        'current_user': request.user,
        'webrtc_ice_servers': settings.WEBRTC_ICE_SERVERS,
        'webrtc_force_relay': settings.WEBRTC_FORCE_RELAY,
    }
    return render(request, 'video/video_room.html', context)

@login_required
def end_call(request, room_id):
    call = get_object_or_404(VideoCall, room_id=room_id)
    
    # Check if user is participant
    if call.caller != request.user and call.receiver != request.user:
        return JsonResponse({'error': 'Not authorized'}, status=403)
    
    # Only end if not already ended
    if call.status != 'ended':
        call.status = 'ended'
        call.ended_at = timezone.now()
        
        # Calculate duration in seconds
        if call.started_at:
            duration = (call.ended_at - call.started_at).total_seconds()
            call.duration = int(duration)
        
        call.save()
    
    return JsonResponse({'status': 'success'})


@login_required
def decline_call(request, room_id):
    """Receiver declined the call — mark missed and notify caller via WebSocket."""
    call = get_object_or_404(VideoCall, room_id=room_id)

    if call.receiver != request.user:
        return JsonResponse({'error': 'Not authorized'}, status=403)

    if call.status == 'calling':
        call.status = 'missed'
        call.ended_at = timezone.now()
        call.save()

    # Notify caller that receiver declined
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'notifications_{call.caller_id}',
        {
            'type': 'call_declined',
            'receiver': request.user.username,
            'room_id': room_id,
        }
    )

    return JsonResponse({'status': 'declined'})


@login_required
def submit_call_rating(request, room_id):
    if request.method != 'POST':
        return redirect('video:call_list')

    call = get_object_or_404(VideoCall, room_id=room_id)

    # Check if user is participant
    if call.caller != request.user and call.receiver != request.user:
        messages.error(request, 'You are not allowed to rate this call.')
        return redirect('video:call_list')

    if call.status != 'ended':
        messages.error(request, 'You can only rate calls after they are ended.')
        return redirect('video:call_list')

    rated_user = call.receiver if call.caller == request.user else call.caller

    try:
        teaching_rating = int(request.POST.get('teaching_rating', 0))
        learning_rating = int(request.POST.get('learning_rating', 0))
    except (TypeError, ValueError):
        messages.error(request, 'Please choose valid ratings.')
        return redirect('video:call_list')

    if teaching_rating not in [1, 2, 3, 4, 5] or learning_rating not in [1, 2, 3, 4, 5]:
        messages.error(request, 'Ratings must be between 1 and 5.')
        return redirect('video:call_list')

    VideoCallRating.objects.update_or_create(
        call=call,
        rater=request.user,
        defaults={
            'rated_user': rated_user,
            'teaching_rating': teaching_rating,
            'learning_rating': learning_rating,
        },
    )

    messages.success(request, f'You rated {rated_user.username} successfully.')
    return redirect('video:call_list')
