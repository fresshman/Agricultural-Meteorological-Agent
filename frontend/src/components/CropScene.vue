<template>
  <div
    ref="root"
    class="crop-scene"
    :class="{ 'is-bursting': bursting }"
    :style="styleVars"
    :data-paused="visible ? 'false' : 'true'"
    aria-hidden="true"
  >
    <div class="crop-scene__ground"></div>
    <svg class="crop-scene__svg" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet" focusable="false">
      <!-- 太阳：固定角标，只做呼吸，不抢主体 -->
      <g v-if="sunny" class="sun">
        <circle cx="82" cy="16" r="10" fill="var(--gold-500)" opacity=".14" />
        <circle cx="82" cy="16" r="6" fill="var(--gold-500)" opacity=".85" />
      </g>

      <!-- 降雨：由 ambient.rain 驱动，0 时不画 -->
      <g v-if="rain > 0" class="rain" :style="{ opacity: 0.25 + rain * 0.5 }">
        <line
          v-for="d in drops"
          :key="'d' + d.i"
          :x1="d.x"
          :y1="d.y"
          :x2="d.x - 1.6"
          :y2="d.y + 7"
          stroke="var(--sky-500)"
          stroke-width="1"
          stroke-linecap="round"
          :style="{ animationDelay: `-${d.delay}s` }"
        />
      </g>

      <!-- 土壤由外层 CSS 通栏绘制：SVG 等比居中时土层不会被缩成中间一块 -->

      <!-- 植株主体：整株绕根部摆动 -->
      <g class="plant">
        <!-- 禾本（高秆 / 密植） -->
        <template v-if="family === 'tall_grass' || family === 'dense_grass'">
          <path
            v-for="s in scene.stalks"
            :key="'st' + s.i"
            :d="s.d"
            fill="none"
            stroke="var(--stem)"
            :stroke-width="family === 'tall_grass' ? 2.6 : 1.7"
            stroke-linecap="round"
          />

          <template v-if="family === 'tall_grass'">
            <path
              v-for="l in scene.leaves"
              :key="'tl' + l.i"
              :d="leafPath(l)"
              fill="none"
              stroke="var(--leaf)"
              stroke-width="2.2"
              stroke-linecap="round"
            />
            <path
              v-if="flowering"
              :d="`M50 ${scene.top} l-4 -6 M50 ${scene.top} l0 -8 M50 ${scene.top} l4 -6`"
              stroke="var(--accent)"
              stroke-width="1.5"
              stroke-linecap="round"
            />
            <ellipse
              v-if="fruiting"
              :cx="scene.cob.x"
              :cy="scene.cob.y"
              :rx="scene.cob.rx"
              :ry="scene.cob.ry"
              fill="var(--fruit)"
              :transform="`rotate(${scene.cob.rot} ${scene.cob.x} ${scene.cob.y})`"
            />
          </template>

          <g v-else-if="flowering || fruiting">
            <ellipse
              v-for="s in scene.stalks"
              :key="'ear' + s.i"
              :cx="s.tipX"
              :cy="s.tipY - 2"
              rx="1.7"
              ry="4"
              :fill="fruiting ? 'var(--fruit)' : 'var(--accent)'"
              :transform="`rotate(${s.lean} ${s.tipX} ${s.tipY - 2})`"
              opacity=".95"
            />
          </g>
        </template>

        <!-- 豆类 -->
        <template v-else-if="family === 'legume'">
          <path
            :d="`M50 84 L50 ${scene.top}`"
            stroke="var(--stem)"
            stroke-width="2.4"
            stroke-linecap="round"
          />
          <ellipse
            v-for="l in scene.broadLeaves"
            :key="'lg' + l.i"
            :cx="l.x"
            :cy="l.y"
            :rx="l.rx"
            :ry="l.ry"
            fill="var(--leaf)"
            :transform="`rotate(${l.rot} ${l.x} ${l.y})`"
            opacity=".92"
          />
          <circle
            v-for="f in scene.flowers"
            :key="'lf' + f.i"
            :cx="f.x"
            :cy="f.y"
            :r="f.r"
            fill="var(--accent)"
          />
          <ellipse
            v-for="g in scene.fruits"
            :key="'lp' + g.i"
            :cx="g.x"
            :cy="g.y + 2"
            rx="1.5"
            ry="3.2"
            fill="var(--fruit)"
            :transform="`rotate(${g.x > 50 ? 18 : -18} ${g.x} ${g.y + 2})`"
          />
        </template>

        <!-- 根茎（马铃薯 / 胡萝卜）：地上叶片 + 地下膨大 -->
        <template v-else-if="family === 'tuber'">
          <ellipse
            v-for="l in scene.broadLeaves"
            :key="'tb' + l.i"
            :cx="l.x"
            :cy="l.y"
            :rx="l.rx"
            :ry="l.ry"
            fill="var(--leaf)"
            :transform="`rotate(${l.rot} ${l.x} ${l.y})`"
            opacity=".92"
          />
          <circle
            v-for="f in scene.flowers"
            :key="'tf' + f.i"
            :cx="f.x"
            :cy="f.y"
            :r="f.r"
            fill="var(--accent)"
          />
          <ellipse
            v-if="fruiting"
            :cx="50"
            :cy="scene.tuber.cy"
            :rx="scene.tuber.rx"
            :ry="scene.tuber.ry"
            fill="var(--fruit)"
            opacity=".95"
          />
        </template>

        <!-- 叶菜莲座 -->
        <template v-else-if="family === 'rosette_leaf'">
          <ellipse
            v-for="l in scene.rosetteLeaves"
            :key="'rl' + l.i"
            :cx="l.x"
            :cy="l.y"
            :rx="l.rx"
            :ry="l.ry"
            fill="var(--leaf)"
            :transform="`rotate(${l.rot} ${l.x} ${l.y})`"
            opacity=".92"
          />
          <circle
            v-if="fruiting && crop === '白菜'"
            :cx="50"
            :cy="scene.head.y"
            :r="scene.head.r"
            fill="var(--leaf)"
          />
          <circle
            v-if="fruiting && crop === '白菜'"
            :cx="50"
            :cy="scene.head.y"
            :r="scene.head.r * 0.55"
            fill="var(--accent)"
            opacity=".35"
          />
        </template>

        <!-- 茄果瓜类 -->
        <template v-else-if="family === 'solanaceous'">
          <path
            :d="`M50 84 L50 ${scene.top}`"
            stroke="var(--stem)"
            stroke-width="2.4"
            stroke-linecap="round"
          />
          <line
            x1="38"
            y1="84"
            x2="38"
            :y2="scene.top + 4"
            stroke="var(--text-disabled)"
            stroke-width="1"
            stroke-dasharray="2 2"
            opacity=".55"
          />
          <ellipse
            v-for="l in scene.broadLeaves"
            :key="'sl' + l.i"
            :cx="l.x"
            :cy="l.y"
            :rx="l.rx"
            :ry="l.ry"
            fill="var(--leaf)"
            :transform="`rotate(${l.rot} ${l.x} ${l.y})`"
            opacity=".92"
          />
          <circle
            v-for="f in scene.flowers"
            :key="'sf' + f.i"
            :cx="f.x"
            :cy="f.y"
            :r="f.r"
            fill="var(--accent)"
          />
          <circle
            v-for="g in scene.fruits"
            :key="'sg' + g.i"
            :cx="g.x"
            :cy="g.y"
            :r="g.r"
            fill="var(--fruit)"
          />
        </template>

        <!-- 木本藤本 -->
        <template v-else-if="family === 'woody'">
          <path
            :d="scene.trunkPath"
            fill="none"
            stroke="var(--stem)"
            stroke-width="2.8"
            stroke-linecap="round"
          />
          <circle
            v-for="(c, i) in scene.canopy"
            :key="'c' + i"
            :cx="c.cx"
            :cy="c.cy"
            :r="c.r"
            fill="var(--leaf)"
            opacity=".92"
          />
          <circle
            v-for="f in scene.flowers"
            :key="'wf' + f.i"
            :cx="f.x"
            :cy="f.y"
            :r="f.r"
            fill="var(--accent)"
          />
          <circle
            v-for="g in scene.fruits"
            :key="'wg' + g.i"
            :cx="g.x"
            :cy="g.y"
            :r="g.r"
            fill="var(--fruit)"
          />
        </template>

        <!-- 花卉 / 多肉 -->
        <template v-else>
          <template v-if="succulent">
            <ellipse
              v-for="l in scene.rosetteLeaves"
              :key="'su' + l.i"
              :cx="l.x"
              :cy="l.y"
              :rx="l.rx"
              :ry="l.ry"
              fill="var(--leaf)"
              :transform="`rotate(${l.rot} ${l.x} ${l.y})`"
              opacity=".94"
            />
            <circle v-if="flowering" cx="50" :cy="scene.top" r="2" fill="var(--accent)" />
          </template>
          <template v-else>
            <g v-for="s in scene.stems" :key="'fs' + s.i">
              <path
                :d="s.d"
                fill="none"
                stroke="var(--stem)"
                stroke-width="1.8"
                stroke-linecap="round"
              />
              <g v-if="flowering" :transform="`translate(${s.tipX} ${s.tipY})`">
                <circle
                  v-for="p in petals"
                  :key="p.k"
                  :cx="p.x"
                  :cy="p.y"
                  r="2.1"
                  fill="var(--accent)"
                />
                <circle cx="0" cy="0" r="1.4" fill="var(--fruit)" />
              </g>
              <circle v-else-if="fruiting" :cx="s.tipX" :cy="s.tipY" r="1.8" fill="var(--fruit)" />
            </g>
          </template>
        </template>
      </g>

      <!-- 收获：一次性迸发，不循环 -->
      <g v-if="bursting" class="burst">
        <circle
          v-for="s in sparks"
          :key="'b' + s.i"
          :cx="50"
          :cy="scene.top + 8"
          r="1.6"
          fill="var(--fruit)"
          :style="{ '--dx': `${s.dx}px`, '--dy': `${s.dy}px` }"
        />
      </g>
    </svg>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { getCropVisual, hash01 } from '@/utils/cropVisuals'

const props = defineProps({
  crop: { type: String, default: '' },
  /** 后端/表单里的阶段名，优先生效 */
  stage: { type: String, default: '' },
  /** buildGrowthModel 的结果，无表单阶段时用它推演 */
  growth: { type: Object, default: null },
  /** 地块 id，用于固定摆动相位 */
  fieldId: { type: String, default: '' },
  /** 正方形像素尺寸；不传则填满父容器 */
  size: { type: [Number, String], default: null },
  /** { rain: 0~1, wind: 0~1 } */
  ambient: { type: Object, default: () => ({}) },
  sunny: { type: Boolean, default: true },
  /** 置为 true 触发一次收获迸发 */
  harvest: { type: Boolean, default: false }
})

const GROUND_Y = 84

const root = ref(null)
const visible = ref(true)
const bursting = ref(false)
let observer = null
let burstTimer = null

const visual = computed(() =>
  getCropVisual(props.crop, {
    stage: props.stage,
    growth: props.growth,
    seed: props.fieldId || props.crop
  })
)

const family = computed(() => visual.value.family)
const crop = computed(() => visual.value.crop)
const flowering = computed(() => visual.value.flowering)
const fruiting = computed(() => visual.value.fruiting)
const succulent = computed(() => visual.value.crop === '多肉植物')
const seed = computed(() => props.fieldId || visual.value.crop)

const rain = computed(() => Math.max(0, Math.min(1, Number(props.ambient?.rain) || 0)))

const styleVars = computed(() => {
  const wind = Math.max(0, Math.min(1, Number(props.ambient?.wind) || 0))
  const v = visual.value
  return {
    ...(props.size ? { width: `${props.size}px`, height: `${props.size}px` } : {}),
    '--stem': v.colors.stem,
    '--leaf': v.colors.leaf,
    '--accent': v.colors.accent,
    '--fruit': v.colors.fruit,
    '--soil': v.colors.soil,
    '--soil-dark': v.colors.soilDark,
    '--sway-amp': (v.sway.amp * (1 + wind * 1.5)).toFixed(2),
    '--sway-dur': `${v.sway.speed}s`,
    '--phase': v.sway.phase.toFixed(3)
  }
})

/** 所有几何量集中算好，模板里只做取值，避免把布局逻辑散进 HTML */
const scene = computed(() => {
  const v = visual.value
  const s = seed.value
  const h = 62 * v.height
  const w = 46 * v.width
  const top = GROUND_Y - h

  const leaves = Array.from({ length: v.leafCount }, (_, i) => {
    const t = v.leafCount === 1 ? 0.5 : i / (v.leafCount - 1)
    const side = i % 2 === 0 ? -1 : 1
    const j = hash01(`${s}L${i}`)
    const len = 5.5 + 4.5 * (0.6 + 0.4 * (1 - t)) * (0.85 + 0.3 * j)
    return {
      i,
      side,
      x: 50 + side * w * (0.6 + 0.3 * j),
      y: GROUND_Y - 5 - t * Math.max(4, h - 10),
      len,
      rot: side * (22 + 20 * j)
    }
  })

  const broadLeaves = leaves.map((l) => ({ ...l, rx: l.len, ry: l.len * 0.42 }))

  const rosetteCount = Math.max(5, v.leafCount)
  const rosetteLeaves = Array.from({ length: rosetteCount }, (_, i) => {
    const angle = -72 + (144 * i) / (rosetteCount - 1)
    const rad = (angle * Math.PI) / 180
    const len = w * (0.75 + 0.25 * hash01(`${s}R${i}`))
    return {
      i,
      x: 50 + Math.sin(rad) * len * 1.15,
      y: GROUND_Y - 3 - Math.cos(rad) * len * 0.55,
      rx: len,
      ry: len * 0.5,
      rot: angle
    }
  })

  let stalks
  if (v.family === 'tall_grass') {
    stalks = [{
      i: 0,
      lean: 0,
      tipX: 50,
      tipY: top,
      d: `M50 84 C 48 ${84 - h * 0.4}, 51 ${84 - h * 0.8}, 50 ${top}`
    }]
  } else {
    const n = Math.max(4, v.leafCount + 1)
    stalks = Array.from({ length: n }, (_, i) => {
      const spread = (i / (n - 1) - 0.5) * 2
      const j = hash01(`${s}S${i}`)
      const tipX = 50 + spread * w * 0.95
      const tipY = GROUND_Y - h * (0.7 + 0.3 * j)
      return {
        i,
        lean: spread * 7,
        tipX,
        tipY,
        d: `M50 84 Q ${50 + spread * w * 0.3} ${GROUND_Y - h * 0.55}, ${tipX} ${tipY}`
      }
    })
  }

  const flowers = v.flowering
    ? Array.from({ length: v.family === 'woody' ? 6 : 3 }, (_, i) => ({
        i,
        x: 50 + (hash01(`${s}Fx${i}`) - 0.5) * w * 1.7,
        y: GROUND_Y - h * (0.66 + 0.28 * hash01(`${s}Fy${i}`)),
        r: 1.7 + hash01(`${s}Fr${i}`) * 1.1
      }))
    : []

  const fruits = v.fruiting
    ? Array.from({ length: v.family === 'woody' ? 5 : 3 }, (_, i) => ({
        i,
        x: 50 + (hash01(`${s}Gx${i}`) - 0.5) * w * 1.55,
        y: GROUND_Y - h * (0.58 + 0.26 * hash01(`${s}Gy${i}`)),
        r: 2.2 + hash01(`${s}Gr${i}`) * 1.3
      }))
    : []

  const canopyR = Math.max(5, w * 0.85)
  const canopyCy = GROUND_Y - h * 0.72
  const canopy = [
    { cx: 50 - w * 0.55, cy: canopyCy + canopyR * 0.25, r: canopyR },
    { cx: 50 + w * 0.55, cy: canopyCy + canopyR * 0.2, r: canopyR * 1.05 },
    { cx: 50, cy: canopyCy - canopyR * 0.35, r: canopyR * 1.1 }
  ]

  const trunkTop = GROUND_Y - h * 0.55
  const trunkPath = `M50 84 L50 ${trunkTop} M50 ${GROUND_Y - h * 0.35} L${50 - w * 0.5} ${GROUND_Y - h * 0.62} M50 ${GROUND_Y - h * 0.4} L${50 + w * 0.5} ${GROUND_Y - h * 0.68}`

  const stems = Array.from({ length: 3 }, (_, i) => {
    const spread = i - 1
    const tipX = 50 + spread * w * 0.8
    const tipY = GROUND_Y - h * (0.8 + 0.15 * hash01(`${s}T${i}`))
    return {
      i,
      tipX,
      tipY,
      d: `M50 84 Q ${50 + spread * w * 0.35} ${GROUND_Y - h * 0.5}, ${tipX} ${tipY}`
    }
  })

  return {
    h,
    w,
    top,
    leaves,
    broadLeaves,
    rosetteLeaves,
    stalks,
    flowers,
    fruits,
    canopy,
    trunkPath,
    stems,
    cob: { x: 44.5, y: GROUND_Y - h * 0.52, rx: 3, ry: 6.6, rot: -14 },
    tuber: { cy: 85, rx: 5 + w * 0.35, ry: 4.2 },
    head: { y: GROUND_Y - w * 0.55, r: Math.max(5, w * 0.9) }
  }
})

/** 叶片路径（禾本科用线条而不是色块，视觉更轻） */
function leafPath(l) {
  const x2 = 50 + l.side * l.len * 1.4
  const y2 = l.y - l.len * 0.8
  return `M50 ${l.y} Q ${50 + l.side * l.len * 0.45} ${l.y - l.len * 0.15}, ${x2} ${y2}`
}

const petals = Array.from({ length: 5 }, (_, k) => {
  const a = (k / 5) * Math.PI * 2 - Math.PI / 2
  return { k, x: Math.cos(a) * 2.6, y: Math.sin(a) * 2.6 }
})

const drops = computed(() =>
  Array.from({ length: 6 }, (_, i) => ({
    i,
    x: 10 + 15 * i + hash01(`${seed.value}D${i}`) * 4,
    y: 12 + hash01(`${seed.value}Y${i}`) * 28,
    delay: hash01(`${seed.value}P${i}`) * 1.1
  }))
)

const sparks = computed(() =>
  Array.from({ length: 8 }, (_, i) => {
    const a = (i / 8) * Math.PI * 2
    const dist = 12 + 6 * hash01(`${seed.value}B${i}`)
    return { i, dx: (Math.cos(a) * dist).toFixed(1), dy: (Math.sin(a) * dist * 0.8 - 5).toFixed(1) }
  })
)

watch(
  () => props.harvest,
  (val) => {
    if (!val) return
    bursting.value = true
    clearTimeout(burstTimer)
    burstTimer = setTimeout(() => {
      bursting.value = false
    }, 1000)
  }
)

onMounted(() => {
  if (typeof IntersectionObserver === 'undefined' || !root.value) return
  observer = new IntersectionObserver(
    ([entry]) => {
      visible.value = Boolean(entry?.isIntersecting)
    },
    { threshold: 0 }
  )
  observer.observe(root.value)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  clearTimeout(burstTimer)
})
</script>

<style scoped>
.crop-scene {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border-radius: inherit;
  background: linear-gradient(180deg, var(--sky-100) 0%, var(--bg-subtle) 62%, var(--bg-subtle) 100%);
}

html.dark .crop-scene {
  background: linear-gradient(180deg, #16332a 0%, #12241c 62%, #12241c 100%);
}

.crop-scene__svg {
  position: relative;
  display: block;
  width: 100%;
  height: 100%;
}

/* 基线固定在 84%，与 SVG 里植株根部对齐 */
.crop-scene__ground {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 16%;
  background: var(--soil);
}

.crop-scene__ground::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  height: 2px;
  background: var(--soil-dark);
  opacity: 0.6;
}

.plant {
  transform-box: view-box;
  transform-origin: 50px 84px;
  animation: crop-sway var(--sway-dur, 4s) ease-in-out infinite alternate;
  animation-delay: calc(var(--phase, 0) * -6s);
  will-change: transform;
}

.sun {
  transform-box: view-box;
  transform-origin: 82px 16px;
  animation: crop-sun 7s ease-in-out infinite;
}

.rain line {
  animation: crop-rain 1.1s linear infinite;
}

.burst circle {
  animation: crop-burst 0.9s ease-out forwards;
}

/* 滚出视口后暂停动画，列表页长滚动时别空转 */
.crop-scene[data-paused='true'] .plant,
.crop-scene[data-paused='true'] .sun,
.crop-scene[data-paused='true'] .rain line {
  animation-play-state: paused;
}

@keyframes crop-sway {
  from {
    transform: rotate(calc(var(--sway-amp, 1) * -1deg));
  }
  to {
    transform: rotate(calc(var(--sway-amp, 1) * 1deg));
  }
}

@keyframes crop-sun {
  0%,
  100% {
    opacity: 0.9;
  }
  50% {
    opacity: 0.55;
  }
}

@keyframes crop-rain {
  from {
    transform: translateY(-4px);
    opacity: 0.9;
  }
  to {
    transform: translateY(16px);
    opacity: 0;
  }
}

@keyframes crop-burst {
  from {
    transform: translate(0, 0) scale(0.4);
    opacity: 1;
  }
  to {
    transform: translate(var(--dx, 0), var(--dy, 0)) scale(1.2);
    opacity: 0;
  }
}
</style>
