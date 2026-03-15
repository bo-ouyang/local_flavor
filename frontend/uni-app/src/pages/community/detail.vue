<template>
  <view class="page">
    <view v-if="post" class="content">
      <view class="hero">
        <swiper class="hero-swiper" indicator-dots circular>
          <swiper-item v-for="img in galleryImages" :key="img">
            <image :src="img" mode="aspectFill" class="hero-image" />
          </swiper-item>
        </swiper>
        <view class="hero-mask"></view>
      </view>

      <view class="post-card">
        <view class="author-row">
          <view class="author-meta">
            <image :src="post.user?.avatar || defaultAvatar" mode="aspectFill" class="avatar" />
            <view class="author-text">
              <view class="author-name-row">
                <text class="author-name">{{ post.user?.nickname || fallbackUser(post.user_id) }}</text>
                <text v-if="post.author_tag" class="author-tag">{{ post.author_tag }}</text>
              </view>
              <text class="author-time">{{ formatDate(post.created_at) }}</text>
            </view>
          </view>
          <view
            class="like-pill"
            :class="{ liked: post.is_liked }"
            @click.stop="toggleLike"
          >
            <text class="like-pill-icon">{{ post.is_liked ? '♥' : '♡' }}</text>
            <text class="like-pill-text">{{ post.like_count || 0 }}</text>
          </view>
        </view>

        <view v-if="isOwner && post.audit_status !== 'approved'" class="audit-box">
          <text class="audit-title">{{ auditTitle }}</text>
          <text class="audit-desc">{{ auditDescription }}</text>
        </view>

        <view v-if="isOwner" class="manage-row">
          <text class="manage-btn danger" @click="deletePost">删除帖子</text>
        </view>

        <view class="item-card">
          <image :src="itemCover" mode="aspectFill" class="item-cover" />
          <view class="item-info">
            <text class="item-title">{{ post.item?.title || '交换特产' }}</text>
            <text class="item-meta">{{ post.item?.city || post.item?.province || '未知地区' }}</text>
            <text class="item-tip">{{ post.exchange_hint || '仅参与过该特产交换的用户可评论' }}</text>
          </view>
        </view>

        <text class="post-content">{{ post.content || '暂无内容' }}</text>

        <view v-if="post.images?.length" class="image-grid">
          <image
            v-for="img in post.images"
            :key="img"
            :src="img"
            mode="aspectFill"
            class="content-image"
            @click="previewImage(img)"
          />
        </view>
      </view>

      <view class="comments-card">
        <view class="comments-head">
          <text class="comments-title">交流评论</text>
          <text class="comments-count">{{ post.comment_count || 0 }} 条</text>
        </view>

        <view v-if="flatComments.length" class="comments-list">
          <view
            v-for="comment in flatComments"
            :key="comment.id"
            class="comment-item"
            :style="{ marginLeft: `${comment.level * 24}rpx` }"
            @click="startReply(comment)"
          >
            <view class="comment-line"></view>
            <view class="comment-body">
              <view class="comment-top">
                <text class="comment-user">{{ comment.user?.nickname || fallbackUser(comment.user_id) }}</text>
                <text class="comment-time">{{ formatDate(comment.created_at) }}</text>
              </view>
              <text class="comment-content">{{ comment.content }}</text>
              <view class="comment-actions">
                <text class="comment-action">
                  {{ comment.level > 0 ? '继续回复' : '回复这条评论' }}
                </text>
                <text
                  v-if="canDeleteComment(comment)"
                  class="comment-delete"
                  @click.stop="deleteComment(comment)"
                >
                  删除
                </text>
              </view>
            </view>
          </view>
        </view>

        <view v-else class="empty">还没有交流评论</view>
      </view>
    </view>

    <view v-else class="loading-state">加载中...</view>

    <view class="composer">
      <view v-if="canComment" class="composer-inner">
        <view v-if="replyTo" class="reply-banner">
          <text class="reply-text">回复 {{ replyTo.user?.nickname || fallbackUser(replyTo.user_id) }}</text>
          <text class="reply-cancel" @click.stop="cancelReply">取消</text>
        </view>
        <view class="input-row">
          <input
            v-model="commentText"
            :placeholder="replyPlaceholder"
            class="input"
            maxlength="500"
          />
          <button class="send-btn" size="mini" :loading="submitting" @click="submitComment">发送</button>
        </view>
      </view>
      <view v-else class="locked-box">
        <text class="locked-title">评论受限</text>
        <text class="locked-desc">只有参与过这个特产交换的用户才能评论该动态</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { onLoad, onPullDownRefresh } from '@dcloudio/uni-app'
import request from '@/utils/request'
import { ensureAuthed } from '@/utils/auth'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const post = ref<any>(null)
const commentsTree = ref<any[]>([])
const commentText = ref('')
const replyTo = ref<any>(null)
const submitting = ref(false)
const postId = ref('')
const defaultAvatar = 'https://dummyimage.com/200x200/e2e8f0/94a3b8&text=User'
const defaultCover = 'https://dummyimage.com/800x600/f1f5f9/94a3b8&text=Community'

const canComment = computed(() => !!post.value?.can_comment)
const isOwner = computed(() => !!post.value && post.value.user_id === userStore.userInfo.id)
const auditTitle = computed(() => {
  if (post.value?.audit_status === 'rejected') return '内容未通过审核'
  return '内容审核中'
})
const auditDescription = computed(() => {
  if (post.value?.audit_status === 'rejected') {
    return post.value?.audit_reason || '请修改内容后重新发布。'
  }
  return '审核通过后会在社区列表中公开展示。'
})

const itemCover = computed(() => {
  if (Array.isArray(post.value?.item?.images) && post.value.item.images.length) {
    return post.value.item.images[0]
  }
  return defaultCover
})

const galleryImages = computed(() => {
  const images = Array.isArray(post.value?.images) ? post.value.images : []
  if (images.length) return images
  return [itemCover.value]
})

const flatComments = computed(() => {
  const rows: any[] = []
  const walk = (nodes: any[], level = 0) => {
    ;(nodes || []).forEach((node) => {
      rows.push({ ...node, level })
      if (Array.isArray(node.replies) && node.replies.length) {
        walk(node.replies, level + 1)
      }
    })
  }
  walk(commentsTree.value, 0)
  return rows
})

const replyPlaceholder = computed(() => {
  if (replyTo.value) {
    return `回复 ${replyTo.value.user?.nickname || '用户'}...`
  }
  return '分享这次交换后的感受...'
})

const fallbackUser = (userId?: number) => `用户${userId || ''}`

const formatDate = (value?: string) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const yyyy = date.getFullYear()
  const mm = `${date.getMonth() + 1}`.padStart(2, '0')
  const dd = `${date.getDate()}`.padStart(2, '0')
  const hh = `${date.getHours()}`.padStart(2, '0')
  const mi = `${date.getMinutes()}`.padStart(2, '0')
  return `${yyyy}-${mm}-${dd} ${hh}:${mi}`
}

const previewImage = (current: string) => {
  uni.previewImage({
    current,
    urls: galleryImages.value
  })
}

const canDeleteComment = (comment: any) => {
  return comment.user_id === userStore.userInfo.id || isOwner.value
}

const toggleLike = async () => {
  if (!post.value?.id) return
  if (!ensureAuthed({ toast: '请先登录后点赞' })) return
  try {
    const res: any = await request.authPost(`/community/posts/${post.value.id}/like`)
    post.value.is_liked = !!res?.liked
    post.value.like_count = Number(res?.like_count || 0)
  } catch (error) {
    console.error('toggle detail like failed', error)
  }
}

const deletePost = async () => {
  if (!isOwner.value || !post.value?.id) return
  const res = await new Promise<boolean>((resolve) => {
    uni.showModal({
      title: '删除帖子',
      content: '删除后帖子将不再展示，是否继续？',
      success: (modalRes) => resolve(!!modalRes.confirm),
      fail: () => resolve(false)
    })
  })
  if (!res) return
  try {
    await request.authDelete(`/community/posts/${post.value.id}`)
    uni.showToast({ title: '已删除', icon: 'success' })
    setTimeout(() => {
      uni.navigateBack()
    }, 300)
  } catch (error) {
    console.error('delete community post failed', error)
  }
}

const deleteComment = async (comment: any) => {
  const confirmed = await new Promise<boolean>((resolve) => {
    uni.showModal({
      title: '删除评论',
      content: '删除后评论将不再展示，是否继续？',
      success: (modalRes) => resolve(!!modalRes.confirm),
      fail: () => resolve(false)
    })
  })
  if (!confirmed) return
  try {
    await request.authDelete(`/community/posts/${postId.value}/comments/${comment.id}`)
    uni.showToast({ title: '评论已删除', icon: 'success' })
    await reloadPage()
  } catch (error) {
    console.error('delete community comment failed', error)
  }
}

const loadDetail = async () => {
  if (!postId.value) return
  const res: any = await request.get(`/community/posts/${postId.value}`)
  post.value = res
}

const loadComments = async () => {
  if (!postId.value) return
  const res: any = await request.get(`/community/posts/${postId.value}/comments`, { root_limit: 100 })
  commentsTree.value = Array.isArray(res) ? res : []
}

const reloadPage = async (refresh = false) => {
  try {
    await Promise.all([loadDetail(), loadComments()])
  } catch (error) {
    console.error('load community detail failed', error)
  } finally {
    if (refresh) uni.stopPullDownRefresh()
  }
}

const startReply = (comment: any) => {
  if (!canComment.value) return
  replyTo.value = comment
}

const cancelReply = () => {
  replyTo.value = null
}

const submitComment = async () => {
  const content = commentText.value.trim()
  if (!content) return
  if (!ensureAuthed({ toast: '请先登录后评论' })) return
  if (!postId.value) return

  submitting.value = true
  try {
    const payload: any = { content }
    if (replyTo.value?.id) payload.parent_id = replyTo.value.id
    await request.authPost(`/community/posts/${postId.value}/comments`, payload)
    uni.showToast({ title: '评论成功', icon: 'success' })
    commentText.value = ''
    replyTo.value = null
    await reloadPage()
  } catch (error) {
    console.error('submit community comment failed', error)
  } finally {
    submitting.value = false
  }
}

onLoad(async (options: any) => {
  postId.value = String(options?.id || '')
  await reloadPage()
})

onPullDownRefresh(async () => {
  await reloadPage(true)
})
</script>

<style>
.page {
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(251, 146, 60, 0.18), transparent 28%),
    linear-gradient(180deg, #fff7ed 0%, #f8fafc 28%, #f8fafc 100%);
  padding-bottom: 180rpx;
}

.content {
  animation: fadeUp 0.28s ease;
}

.hero {
  position: relative;
}

.hero-swiper {
  width: 100%;
  height: 460rpx;
}

.hero-image {
  width: 100%;
  height: 100%;
}

.hero-mask {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 180rpx;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0), rgba(15, 23, 42, 0.38));
}

.post-card,
.comments-card {
  margin: 0 24rpx;
  background: rgba(255, 255, 255, 0.92);
  border: 1rpx solid rgba(226, 232, 240, 0.95);
  box-shadow: 0 16rpx 40rpx rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(8px);
}

.post-card {
  margin-top: -56rpx;
  border-radius: 28rpx;
  padding: 24rpx;
  position: relative;
  z-index: 2;
}

.author-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}

.author-meta {
  display: flex;
  align-items: center;
  gap: 14rpx;
}

.avatar {
  width: 84rpx;
  height: 84rpx;
  border-radius: 50%;
  background: #e2e8f0;
}

.author-text {
  display: flex;
  flex-direction: column;
  gap: 4rpx;
}

.author-name-row {
  display: flex;
  align-items: center;
  gap: 10rpx;
  flex-wrap: wrap;
}

.author-name {
  font-size: 28rpx;
  color: #0f172a;
  font-weight: 700;
}

.author-tag {
  padding: 4rpx 12rpx;
  border-radius: 999rpx;
  background: #fff7ed;
  color: #c2410c;
  font-size: 20rpx;
  border: 1rpx solid #fed7aa;
}

.author-time {
  font-size: 22rpx;
  color: #64748b;
}

.like-pill {
  min-width: 108rpx;
  height: 60rpx;
  padding: 0 18rpx;
  border-radius: 999rpx;
  background: #f8fafc;
  border: 1rpx solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
}

.like-pill.liked {
  background: #fff1f2;
  border-color: #fecdd3;
}

.like-pill-icon {
  color: #e11d48;
  font-size: 24rpx;
  line-height: 1;
}

.like-pill-text {
  font-size: 22rpx;
  color: #475569;
}

.item-card {
  margin-top: 22rpx;
  display: flex;
  gap: 16rpx;
  padding: 16rpx;
  border-radius: 22rpx;
  background: linear-gradient(135deg, #fff7ed, #ffffff);
  border: 1rpx solid #fed7aa;
}

.audit-box {
  margin-top: 18rpx;
  padding: 16rpx 18rpx;
  border-radius: 18rpx;
  background: #fff7ed;
  border: 1rpx solid #fed7aa;
}

.audit-title {
  display: block;
  font-size: 25rpx;
  font-weight: 700;
  color: #9a3412;
}

.audit-desc {
  display: block;
  margin-top: 8rpx;
  font-size: 22rpx;
  line-height: 1.55;
  color: #c2410c;
}

.manage-row {
  margin-top: 16rpx;
  display: flex;
  justify-content: flex-end;
}

.manage-btn {
  padding: 10rpx 16rpx;
  border-radius: 999rpx;
  font-size: 22rpx;
  border: 1rpx solid #e2e8f0;
  color: #475569;
}

.manage-btn.danger {
  border-color: #fecaca;
  background: #fff1f2;
  color: #be123c;
}

.item-cover {
  width: 148rpx;
  height: 148rpx;
  border-radius: 18rpx;
  background: #e2e8f0;
  flex-shrink: 0;
}

.item-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.item-title {
  font-size: 30rpx;
  color: #0f172a;
  font-weight: 700;
  line-height: 1.4;
}

.item-meta {
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #64748b;
}

.item-tip {
  margin-top: 10rpx;
  font-size: 21rpx;
  color: #c2410c;
}

.post-content {
  display: block;
  margin-top: 22rpx;
  font-size: 28rpx;
  line-height: 1.7;
  color: #334155;
}

.image-grid {
  margin-top: 18rpx;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12rpx;
}

.content-image {
  width: 100%;
  height: 220rpx;
  border-radius: 18rpx;
  background: #e2e8f0;
}

.comments-card {
  margin-top: 18rpx;
  border-radius: 24rpx;
  padding: 24rpx;
}

.comments-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18rpx;
}

.comments-title {
  font-size: 32rpx;
  color: #0f172a;
  font-weight: 800;
}

.comments-count {
  font-size: 22rpx;
  color: #ea580c;
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 14rpx;
}

.comment-item {
  display: flex;
  gap: 12rpx;
}

.comment-line {
  width: 6rpx;
  border-radius: 999rpx;
  background: linear-gradient(180deg, #fb923c, #fdba74);
}

.comment-body {
  flex: 1;
  padding: 14rpx 16rpx;
  border-radius: 18rpx;
  background: #f8fafc;
  border: 1rpx solid #e2e8f0;
}

.comment-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14rpx;
}

.comment-user {
  font-size: 25rpx;
  color: #0f172a;
  font-weight: 700;
}

.comment-time {
  font-size: 21rpx;
  color: #94a3b8;
}

.comment-content {
  display: block;
  margin-top: 8rpx;
  font-size: 25rpx;
  line-height: 1.55;
  color: #334155;
}

.comment-action {
  font-size: 21rpx;
  color: #ea580c;
}

.comment-actions {
  margin-top: 10rpx;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12rpx;
}

.comment-delete {
  font-size: 21rpx;
  color: #be123c;
}

.composer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 16rpx 20rpx calc(18rpx + env(safe-area-inset-bottom));
  background: rgba(255, 255, 255, 0.96);
  border-top: 1rpx solid #e2e8f0;
  backdrop-filter: blur(8px);
}

.composer-inner {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}

.reply-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12rpx 16rpx;
  border-radius: 14rpx;
  background: #fff7ed;
  border: 1rpx solid #fed7aa;
}

.reply-text {
  font-size: 22rpx;
  color: #9a3412;
}

.reply-cancel {
  font-size: 22rpx;
  color: #ea580c;
}

.input-row {
  display: flex;
  align-items: center;
  gap: 12rpx;
}

.input {
  flex: 1;
  height: 82rpx;
  border-radius: 999rpx;
  background: #f8fafc;
  border: 1rpx solid #e2e8f0;
  padding: 0 22rpx;
  box-sizing: border-box;
  font-size: 25rpx;
  color: #0f172a;
}

.send-btn {
  height: 82rpx;
  line-height: 82rpx;
  padding: 0 26rpx;
  border-radius: 999rpx;
  background: linear-gradient(135deg, #f97316, #f59e0b);
  color: #fff;
  border: none;
  font-size: 24rpx;
  font-weight: 700;
}

.locked-box {
  padding: 18rpx 20rpx;
  border-radius: 18rpx;
  background: #fff7ed;
  border: 1rpx solid #fed7aa;
}

.locked-title {
  display: block;
  font-size: 25rpx;
  font-weight: 700;
  color: #9a3412;
}

.locked-desc {
  display: block;
  margin-top: 8rpx;
  font-size: 22rpx;
  line-height: 1.5;
  color: #c2410c;
}

.empty,
.loading-state {
  text-align: center;
  color: #94a3b8;
  font-size: 24rpx;
  padding: 80rpx 24rpx;
}

@keyframes fadeUp {
  from {
    opacity: 0;
    transform: translateY(12rpx);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
