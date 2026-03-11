# Complete example: Adding notifications to a new "posts" app
# This shows the full workflow from type definition to integration

# ==============================================================================
# STEP 1: Define notification type in apps/notifications/types.py
# ==============================================================================

from apps.notifications.enums import Category, Channel
from apps.notifications.types import NotificationTypeConfig

NOTIFICATION_TYPES = {
    # ... existing types ...

    # New post published
    'post_published': NotificationTypeConfig(
        name='post_published',
        display_name='Post Published',
        description='Notification when your draft post is published',
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.EMAIL, Channel.PUSH],
        required_context=['post_title', 'post_url'],
        email_template='post_published',
        push_template=None,
        sms_template=None,
        user_configurable=True,
        enabled=True,
    ),

    # Someone commented on your post
    'post_comment': NotificationTypeConfig(
        name='post_comment',
        display_name='Post Comments',
        description='Notification when someone comments on your post',
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.EMAIL, Channel.PUSH],
        required_context=['post_title', 'comment_author', 'comment_text', 'post_url'],
        email_template='post_comment',
        push_template=None,
        sms_template=None,
        user_configurable=True,
        enabled=True,
    ),

    # Post liked (low priority, push only by default)
    'post_liked': NotificationTypeConfig(
        name='post_liked',
        display_name='Post Likes',
        description='Notification when someone likes your post',
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.PUSH],  # Push only, email would be too noisy
        required_context=['post_title', 'liker_name', 'post_url'],
        email_template='post_liked',
        push_template=None,
        sms_template=None,
        user_configurable=True,
        enabled=True,
    ),
}

# ==============================================================================
# STEP 2: Create email templates in Django admin
# ==============================================================================

# Navigate to /admin/email/emailtemplate/add/ and create:

# Template 1: post_published
"""
Name: post_published
Subject: Your post "{{ post_title }}" is now live!
HTML Body:
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1>Your Post is Published!</h1>
    <p>Hello {{ user_name }},</p>
    <p>Great news! Your post <strong>{{ post_title }}</strong> is now live and visible to everyone.</p>
    <table cellpadding="0" cellspacing="0" style="margin: 20px 0;">
        <tr>
            <td style="background-color: #007bff; border-radius: 5px; text-align: center;">
                <a href="{{ post_url }}" style="color: #ffffff; text-decoration: none; padding: 12px 24px; display: inline-block; font-weight: bold;">
                    View Your Post
                </a>
            </td>
        </tr>
    </table>
    <p>Share it with your friends and start the conversation!</p>
    <p>Thanks,<br>The Team</p>
</body>
</html>

Variables:
{
  "post_title": {"type": "string", "required": true},
  "post_url": {"type": "string", "required": true}
}

Category: transactional
Is Active: ✓
"""

# Template 2: post_comment
"""
Name: post_comment
Subject: New comment on "{{ post_title }}"
HTML Body:
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1>New Comment on Your Post</h1>
    <p>Hello {{ user_name }},</p>
    <p><strong>{{ comment_author }}</strong> commented on your post <strong>{{ post_title }}</strong>:</p>
    <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0;">
        <p style="margin: 0; color: #333;">{{ comment_text }}</p>
    </div>
    <table cellpadding="0" cellspacing="0" style="margin: 20px 0;">
        <tr>
            <td style="background-color: #007bff; border-radius: 5px; text-align: center;">
                <a href="{{ post_url }}" style="color: #ffffff; text-decoration: none; padding: 12px 24px; display: inline-block; font-weight: bold;">
                    View Comment
                </a>
            </td>
        </tr>
    </table>
    <p style="font-size: 12px; color: #666;">
        Don't want these notifications? <a href="{{ preferences_url }}">Manage your preferences</a>
    </p>
</body>
</html>

Variables:
{
  "post_title": {"type": "string", "required": true},
  "comment_author": {"type": "string", "required": true},
  "comment_text": {"type": "string", "required": true},
  "post_url": {"type": "string", "required": true}
}

Category: transactional
Is Active: ✓
"""

# Template 3: post_liked
"""
Name: post_liked
Subject: {{ liker_name }} liked your post
HTML Body:
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1>Someone Liked Your Post!</h1>
    <p>Hello {{ user_name }},</p>
    <p><strong>{{ liker_name }}</strong> liked your post <strong>{{ post_title }}</strong>.</p>
    <p><a href="{{ post_url }}">View your post</a></p>
</body>
</html>

Variables:
{
  "post_title": {"type": "string", "required": true},
  "liker_name": {"type": "string", "required": true},
  "post_url": {"type": "string", "required": true}
}

Category: transactional
Is Active: ✓
"""

# ==============================================================================
# STEP 3: Integrate into your posts app
# ==============================================================================

# apps/posts/models.py
from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedModel, UUIDModel

class Post(TimeStampedModel, UUIDModel):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=200)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Draft'),
        ('published', 'Published'),
    ], default='draft')
    published_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title


class Comment(TimeStampedModel, UUIDModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()

    def __str__(self):
        return f"Comment by {self.author} on {self.post}"


class Like(TimeStampedModel):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='likes')

    class Meta:
        unique_together = ('post', 'user')


# apps/posts/services.py
from apps.notifications.services import NotificationService
from apps.posts.models import Post, Comment, Like
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def publish_post(post_id):
    """Publish a draft post and notify author"""
    post = Post.objects.get(id=post_id)

    if post.status == 'published':
        raise ValueError('Post is already published')

    # Update post status
    post.status = 'published'
    post.published_at = timezone.now()
    post.save()

    # Send notification to author
    try:
        NotificationService.send(
            user=post.author,
            notification_type='post_published',
            context={
                'post_title': post.title,
                'post_url': f'https://example.com/posts/{post.id}/',
            }
        )
    except Exception as e:
        # Log error but don't fail the publish operation
        logger.error(f"Failed to send post_published notification: {e}")

    return post


def create_comment(post_id, user, text):
    """Create comment and notify post author"""
    post = Post.objects.get(id=post_id)

    # Create comment
    comment = Comment.objects.create(
        post=post,
        author=user,
        text=text
    )

    # Notify post author (unless commenting on own post)
    if post.author != user:
        try:
            NotificationService.send(
                user=post.author,
                notification_type='post_comment',
                context={
                    'post_title': post.title,
                    'comment_author': user.profile.display_name,
                    'comment_text': text[:200],  # Truncate for preview
                    'post_url': f'https://example.com/posts/{post.id}/#comment-{comment.id}',
                }
            )
        except Exception as e:
            logger.error(f"Failed to send post_comment notification: {e}")

    return comment


def toggle_like(post_id, user):
    """Toggle like on post and notify author"""
    post = Post.objects.get(id=post_id)

    # Toggle like
    like, created = Like.objects.get_or_create(post=post, user=user)

    if not created:
        # Unlike
        like.delete()
        return {'liked': False}

    # Like created - notify post author (unless liking own post)
    if post.author != user:
        try:
            NotificationService.send(
                user=post.author,
                notification_type='post_liked',
                context={
                    'post_title': post.title,
                    'liker_name': user.profile.display_name,
                    'post_url': f'https://example.com/posts/{post.id}/',
                }
            )
        except Exception as e:
            logger.error(f"Failed to send post_liked notification: {e}")

    return {'liked': True}


# apps/posts/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from apps.posts.services import publish_post, create_comment, toggle_like


class PublishPostView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        """Publish a draft post"""
        try:
            post = publish_post(post_id)
            return Response({
                'id': str(post.id),
                'title': post.title,
                'status': post.status,
                'published_at': post.published_at,
            }, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class CreateCommentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        """Create a comment on a post"""
        text = request.data.get('text')

        if not text:
            return Response({'error': 'Text is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            comment = create_comment(post_id, request.user, text)
            return Response({
                'id': str(comment.id),
                'text': comment.text,
                'author': comment.author.profile.display_name,
                'created_at': comment.created_at,
            }, status=status.HTTP_201_CREATED)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)


class ToggleLikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        """Toggle like on a post"""
        try:
            result = toggle_like(post_id, request.user)
            return Response(result, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found'}, status=status.HTTP_404_NOT_FOUND)


# apps/posts/urls.py
from django.urls import path
from apps.posts.views import PublishPostView, CreateCommentView, ToggleLikeView

urlpatterns = [
    path('posts/<uuid:post_id>/publish/', PublishPostView.as_view(), name='publish_post'),
    path('posts/<uuid:post_id>/comments/', CreateCommentView.as_view(), name='create_comment'),
    path('posts/<uuid:post_id>/like/', ToggleLikeView.as_view(), name='toggle_like'),
]


# ==============================================================================
# STEP 4: Test the integration
# ==============================================================================

# apps/posts/tests/test_notifications.py
from django.test import TestCase
from apps.users.models import User
from apps.posts.models import Post
from apps.posts.services import publish_post, create_comment, toggle_like
from apps.notifications.models import NotificationLog


class PostNotificationTestCase(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(email='author@example.com', password='pass')
        self.commenter = User.objects.create_user(email='commenter@example.com', password='pass')

        self.post = Post.objects.create(
            author=self.author,
            title='Test Post',
            content='Test content',
            status='draft'
        )

    def test_publish_post_sends_notification(self):
        """Test that publishing a post sends notification to author"""
        publish_post(self.post.id)

        # Check notification was created
        log = NotificationLog.objects.get(
            user=self.author,
            notification_type='post_published'
        )
        self.assertEqual(log.context['post_title'], 'Test Post')

    def test_comment_sends_notification(self):
        """Test that commenting sends notification to post author"""
        create_comment(self.post.id, self.commenter, 'Great post!')

        # Check notification was sent
        log = NotificationLog.objects.get(
            user=self.author,
            notification_type='post_comment'
        )
        self.assertEqual(log.context['comment_author'], self.commenter.profile.display_name)
        self.assertEqual(log.context['comment_text'], 'Great post!')

    def test_comment_on_own_post_no_notification(self):
        """Test that commenting on own post doesn't send notification"""
        create_comment(self.post.id, self.author, 'Self comment')

        # No notification should be sent
        exists = NotificationLog.objects.filter(
            user=self.author,
            notification_type='post_comment'
        ).exists()
        self.assertFalse(exists)

    def test_like_sends_notification(self):
        """Test that liking sends notification to post author"""
        result = toggle_like(self.post.id, self.commenter)

        self.assertTrue(result['liked'])

        # Check notification was sent
        log = NotificationLog.objects.get(
            user=self.author,
            notification_type='post_liked'
        )
        self.assertEqual(log.context['liker_name'], self.commenter.profile.display_name)


# ==============================================================================
# USAGE SUMMARY
# ==============================================================================

"""
After following this example:

1. Users can control their post notification preferences at:
   GET /api/v1/notifications/preferences/

2. Users will receive notifications via their preferred channels (email/push)
   when:
   - Their draft post is published
   - Someone comments on their post
   - Someone likes their post (push only by default)

3. View notification history:
   GET /api/v1/notifications/history/?notification_type=post_comment

4. All notifications are logged for audit in NotificationLog and EmailLog tables

5. Failed notifications will automatically retry via Celery

6. Email delivery is tracked via SNS webhooks (delivery, bounce, complaint)
"""
