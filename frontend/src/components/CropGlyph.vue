<template>
  <span class="crop-glyph" :style="{ color: color || undefined, width: size + 'px', height: size + 'px' }" :title="label">
    <svg viewBox="0 0 48 48" :width="size" :height="size" fill="none" aria-hidden="true">
      <!-- 玉米 -->
      <g v-if="key === 'corn'">
        <path d="M24 42V20" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" />
        <ellipse cx="24" cy="24" rx="8.5" ry="14" fill="currentColor" />
        <path d="M16.5 19h15M16.5 24h15M16.5 29h15M16.5 34h15" stroke="rgba(255,255,255,.4)" stroke-width="1.4" />
        <path d="M24 40c-7 0-10-7-8-13 3 4 6 8 8 13Z" fill="currentColor" opacity=".5" />
        <path d="M24 40c7 0 10-7 8-13-3 4-6 8-8 13Z" fill="currentColor" opacity=".5" />
      </g>
      <!-- 小麦 -->
      <g v-else-if="key === 'wheat'">
        <path d="M24 43V18" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" />
        <ellipse cx="24" cy="11" rx="3" ry="6.5" fill="currentColor" />
        <ellipse cx="18.5" cy="16" rx="2.4" ry="5.2" fill="currentColor" transform="rotate(-26 18.5 16)" />
        <ellipse cx="29.5" cy="16" rx="2.4" ry="5.2" fill="currentColor" transform="rotate(26 29.5 16)" />
        <ellipse cx="19" cy="23" rx="2.2" ry="4.8" fill="currentColor" transform="rotate(-24 19 23)" />
        <ellipse cx="29" cy="23" rx="2.2" ry="4.8" fill="currentColor" transform="rotate(24 29 23)" />
      </g>
      <!-- 水稻 -->
      <g v-else-if="key === 'rice'">
        <path d="M24 43c0-12 0-20-2-30" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" />
        <g fill="currentColor">
          <ellipse cx="22" cy="10" rx="2.2" ry="5" transform="rotate(18 22 10)" />
          <ellipse cx="27" cy="12" rx="2.2" ry="5" transform="rotate(-14 27 12)" />
          <ellipse cx="21" cy="17" rx="2.1" ry="4.6" transform="rotate(22 21 17)" />
          <ellipse cx="28" cy="19" rx="2.1" ry="4.6" transform="rotate(-18 28 19)" />
          <ellipse cx="23" cy="24" rx="2" ry="4.2" transform="rotate(16 23 24)" />
        </g>
      </g>
      <!-- 大豆 -->
      <g v-else-if="key === 'soy'">
        <path d="M14 33C14 22 34 22 34 33c0 9-20 9-20 0Z" fill="currentColor" />
        <circle cx="21" cy="31" r="2.4" fill="rgba(255,255,255,.55)" />
        <circle cx="27" cy="33" r="2.4" fill="rgba(255,255,255,.55)" />
        <path d="M24 22c6-6 14-4 12 2-6 2-10 0-12-2Z" fill="currentColor" opacity=".6" />
      </g>
      <!-- 马铃薯 -->
      <g v-else-if="key === 'potato'">
        <path d="M13 28c0-9 7-14 14-13 8 1 10 8 6 14-3 5-15 6-20-1Z" fill="currentColor" />
        <path d="M21 16v-5M27 17v-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
        <path d="M21 11c-2-2-1-4 1-4M27 13c2-1 3-3 1-4" stroke="rgba(255,255,255,.5)" stroke-width="1.6" fill="none" stroke-linecap="round" />
      </g>
      <!-- 默认：幼苗 -->
      <g v-else>
        <path d="M24 43V25" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" />
        <path d="M24 29C16 29 12 23 12 17c8 0 12 6 12 12Z" fill="currentColor" />
        <path d="M24 27C32 27 36 21 36 15c-8 0-12 6-12 12Z" fill="currentColor" opacity=".7" />
      </g>
    </svg>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { cropKey, CROP_LABEL } from '@/utils/growth'

const props = defineProps({
  crop: { type: String, default: '' },
  size: { type: Number, default: 36 },
  color: { type: String, default: '' }
})

const key = computed(() => cropKey(props.crop))
const label = computed(() => CROP_LABEL[key.value] || props.crop || '作物')
</script>

<style scoped>
.crop-glyph {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--brand-600);
  line-height: 0;
}
html.dark .crop-glyph {
  color: var(--brand-500);
}
.crop-glyph svg {
  display: block;
}
</style>
