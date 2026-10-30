<template>
  <div class="composer">
    <!-- 快捷问题 chips：点击填充输入框（不自动发送，便于追加上下文） -->
    <div v-if="chips.length" class="composer__chips">
      <button
        v-for="chip in chips"
        :key="chip"
        type="button"
        class="composer__chip"
        :title="chip"
        @click="fillChip(chip)"
      >
        {{ chip }}
      </button>
    </div>

    <div class="composer__box" :class="{ 'is-streaming': streaming }">
      <!-- 语音识别中的实时回显 -->
      <transition name="fade">
        <div v-if="listening && interim" class="composer__interim">
          <el-icon class="composer__interim-icon"><Microphone /></el-icon>
          <span class="composer__interim-text">{{ interim }}</span>
        </div>
      </transition>

      <div class="composer__row">
        <textarea
          ref="taRef"
          v-model="draft"
          class="composer__input"
          :placeholder="placeholder"
          rows="1"
          :disabled="streaming"
          @input="autoGrow"
          @keydown="onKeydown"
        ></textarea>

        <div class="composer__tools">
          <!-- 语音输入：不支持时置灰 + Tooltip -->
          <el-tooltip
            :content="speechSupported ? (listening ? '正在聆听，点击结束' : '语音输入') : '当前浏览器不支持语音，请使用 Chrome 或手动输入'"
            placement="top"
          >
            <button
              type="button"
              class="composer__icon-btn"
              :class="{ 'is-active': listening }"
              :disabled="!speechSupported || streaming"
              :aria-label="listening ? '结束语音输入' : '语音输入'"
              @click="toggleVoice"
            >
              <span class="composer__pulse" aria-hidden="true"></span>
              <el-icon :size="18"><Microphone /></el-icon>
            </button>
          </el-tooltip>

          <!-- 用户类型（记忆到 prefs） -->
          <el-select
            v-model="userTypeLocal"
            class="composer__select"
            size="small"
            :disabled="streaming"
            aria-label="用户类型"
            @change="onUserTypeChange"
          >
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
            <el-option v-for="t in USER_TYPES" :key="t" :label="t" :value="t" />
          </el-select>

          <!-- 作物类型（记忆到 prefs） -->
          <el-select
            v-model="cropTypeLocal"
            class="composer__select"
            size="small"
            :disabled="streaming"
            aria-label="作物类型"
            @change="onCropTypeChange"
          >
            <template #prefix>
              <el-icon><Grape /></el-icon>
            </template>
            <el-option v-for="c in CROP_TYPES" :key="c" :label="c" :value="c" />
          </el-select>

          <!-- 发送 / 停止 -->
          <button
            v-if="streaming"
            type="button"
            class="composer__send composer__send--stop"
            :aria-label="'停止生成'"
            @click="emit('stop')"
          >
            <el-icon :size="16"><VideoPause /></el-icon>
            <span>停止</span>
          </button>
          <button
            v-else
            type="button"
            class="composer__send"
            :disabled="!canSend"
            :aria-label="'发送'"
            @click="onSend"
          >
            <el-icon :size="16"><Promotion /></el-icon>
            <span>发送</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useSpeech } from '@/composables/useSpeech'
import { CROP_TYPES as CROPS } from '@/utils/crops'

const props = defineProps({
  /** 快捷问题列表（点击填充输入框） */
  chips: { type: Array, default: () => [] },
  /** 输入框占位 */
  placeholder: { type: String, default: '问我任何农事问题，如：未来三天玉米适合打药吗？' }
})
const emit = defineEmits(['send', 'stop'])

const chat = useChatStore()
const streaming = computed(() => chat.streaming)

const draft = ref('')
const taRef = ref(null)
const canSend = computed(() => draft.value.trim().length > 0 && !streaming.value)

const USER_TYPES = ['普通农户', '种植大户', '农技人员', '合作社']
const CROP_TYPES = CROPS

const userTypeLocal = ref(chat.userType)
const cropTypeLocal = ref(chat.cropType)
watch(
  () => chat.userType,
  (v) => (userTypeLocal.value = v)
)
watch(
  () => chat.cropType,
  (v) => (cropTypeLocal.value = v)
)

function onUserTypeChange(v) {
  chat.setContext(v, null)
}
function onCropTypeChange(v) {
  chat.setContext(null, v)
}

// ---------------------------------------------------------------- 语音
const { supported: speechSupported, listening, interim, start: startVoice, stop: stopVoice, toggle: toggleVoiceRaw } = useSpeech({
  onResult: (text) => {
    draft.value = draft.value ? `${draft.value}${text}` : text
    autoGrow()
  }
})

function toggleVoice() {
  if (listening.value) stopVoice()
  else startVoice()
}

// ---------------------------------------------------------------- 输入与发送
function fillChip(chip) {
  draft.value = chip
  autoGrow()
  nextTick(() => taRef.value?.focus())
}

function onKeydown(e) {
  // 中文/日文输入法组字阶段，Enter 仅确认候选词，不发送
  if (e.isComposing || e.keyCode === 229) return
  const isEnter = e.key === 'Enter'
  if (isEnter && !e.shiftKey) {
    e.preventDefault()
    onSend()
  } else if (isEnter && (e.metaKey || e.ctrlKey)) {
    e.preventDefault()
    onSend()
  }
}

function onSend() {
  const text = draft.value.trim()
  if (!text || streaming.value) return
  draft.value = ''
  nextTick(autoGrow)
  emit('send', text)
}

/** 文本框高度自适应（最多约 6 行） */
function autoGrow() {
  const el = taRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = `${Math.min(el.scrollHeight, 168)}px`
}

watch(draft, () => nextTick(autoGrow))
onBeforeUnmount(() => stopVoice())
</script>

<style scoped>
.composer {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.composer__chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
}

.composer__chip {
  padding: 4px var(--sp-3);
  font-size: var(--fs-caption);
  color: var(--text-secondary);
  background: var(--bg-subtle);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-full);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
  white-space: nowrap;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}

.composer__chip:hover {
  color: var(--brand-600);
  border-color: var(--brand-300);
  background: var(--brand-50);
}

.composer__box {
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  background: var(--bg-card);
  padding: var(--sp-3);
  transition: border-color var(--dur-fast) var(--ease), box-shadow var(--dur-fast) var(--ease);
}

.composer__box:focus-within {
  border-color: var(--brand-400);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--brand-500) 14%, transparent);
}

.composer__interim {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  margin-bottom: var(--sp-2);
  padding: var(--sp-1) var(--sp-3);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--brand-500) 10%, transparent);
  color: var(--brand-700);
  font-size: var(--fs-sm);
}

html.dark .composer__interim {
  color: var(--brand-300);
}

.composer__interim-icon {
  color: var(--brand-500);
  animation: pulse-soft 1.4s ease-in-out infinite;
}

.composer__row {
  display: flex;
  align-items: flex-end;
  gap: var(--sp-3);
}

.composer__input {
  flex: 1 1 auto;
  min-width: 0;
  resize: none;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text-body);
  font-size: var(--fs-body);
  line-height: var(--lh-body);
  font-family: inherit;
  max-height: 168px;
}

.composer__input::placeholder {
  color: var(--text-disabled);
}

.composer__input:disabled {
  cursor: not-allowed;
}

.composer__tools {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  flex: 0 0 auto;
}

.composer__icon-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
}

.composer__icon-btn:hover:not(:disabled) {
  color: var(--brand-600);
  border-color: var(--brand-300);
  background: var(--brand-50);
}

.composer__icon-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.composer__icon-btn.is-active {
  color: #fff;
  background: var(--brand-500);
  border-color: var(--brand-500);
}

/* 录音脉冲动效（仅在 active 时显示） */
.composer__pulse {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: var(--brand-500);
  opacity: 0;
  pointer-events: none;
}

.composer__icon-btn.is-active .composer__pulse {
  animation: voice-pulse 1.4s ease-out infinite;
}

@keyframes voice-pulse {
  0% {
    transform: scale(0.9);
    opacity: 0.5;
  }
  100% {
    transform: scale(1.5);
    opacity: 0;
  }
}

.composer__select {
  width: 104px;
}

.composer__send {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 var(--sp-4);
  border: 0;
  border-radius: var(--radius-md);
  background: var(--brand-500);
  color: #fff;
  font-size: var(--fs-sm);
  font-weight: 600;
  cursor: pointer;
  transition: background var(--dur-fast) var(--ease), opacity var(--dur-fast) var(--ease);
  white-space: nowrap;
}

.composer__send:hover:not(:disabled) {
  background: var(--brand-600);
}

.composer__send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.composer__send--stop {
  background: var(--state-danger);
}

.composer__send--stop:hover:not(:disabled) {
  background: color-mix(in srgb, var(--state-danger) 86%, #000);
}

@keyframes pulse-soft {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

@media (max-width: 767px) {
  .composer__select {
    width: 88px;
  }
  .composer__send span {
    display: none;
  }
  .composer__send {
    padding: 0 var(--sp-3);
  }
}
</style>
