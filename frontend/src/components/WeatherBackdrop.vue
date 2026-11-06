<template>
  <div
    class="wx-bg"
    :class="[`wx-bg--${sceneInfo.scene}`, { 'wx-bg--night': sceneInfo.night, 'wx-bg--idle': !active }]"
    :style="rootVars"
    aria-hidden="true"
  >
    <div class="wx-bg__sky"></div>

    <!-- 夜间星空：云、雾、降水会遮星，只在晴朗/有风的夜里出现 -->
    <div v-if="active && sceneInfo.night && starrySky" class="wx-bg__stars">
      <span v-for="s in stars" :key="s.id" class="wx-bg__star" :style="s.style"></span>
    </div>

    <!-- 日月：降水/雾天收起，避免「下雨还出太阳」 -->
    <div
      v-if="active && !isWet && sceneInfo.scene !== 'fog'"
      class="wx-bg__orb"
      :class="sceneInfo.night ? 'is-moon' : 'is-sun'"
    ></div>

    <!-- 云层：云量随湿度，漂移速度随风速 -->
    <div v-if="active && showClouds" class="wx-bg__clouds">
      <span v-for="c in clouds" :key="c.id" class="wx-bg__cloud" :style="c.style"></span>
    </div>

    <div v-if="active && sceneInfo.scene === 'rain'" class="wx-bg__rain">
      <span v-for="d in drops" :key="d.id" class="wx-bg__drop" :style="d.style"></span>
    </div>

    <div v-if="active && sceneInfo.scene === 'snow'" class="wx-bg__snow">
      <span v-for="f in flakes" :key="f.id" class="wx-bg__flake" :style="f.style"></span>
    </div>

    <div v-if="active && sceneInfo.scene === 'fog'" class="wx-bg__fog">
      <span v-for="f in fogBands" :key="f.id" class="wx-bg__fog-band" :style="f.style"></span>
    </div>

    <div v-if="active && sceneInfo.scene === 'wind'" class="wx-bg__wind">
      <span v-for="g in gusts" :key="g.id" class="wx-bg__gust" :style="g.style"></span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { resolveWeatherScene } from '@/utils/weatherScene.js'

const props = defineProps({
  temperature: { type: Number, default: null },
  humidity: { type: Number, default: null },
  windSpeed: { type: Number, default: null },
  precipitation: { type: Number, default: null },
  /** 气象源给的天气现象文本；当前订阅可能为空，空了就走实测推演 */
  conditionText: { type: String, default: '' },
  timestamp: { type: String, default: null },
  /** 无可用气象数据时只保留静态底色，不凭空播雨雪 */
  active: { type: Boolean, default: true }
})

const sceneInfo = computed(() =>
  resolveWeatherScene(
    {
      temperature: props.temperature,
      humidity: props.humidity,
      windSpeed: props.windSpeed,
      precipitation: props.precipitation,
      conditionText: props.conditionText,
      timestamp: props.timestamp
    },
    new Date()
  )
)

const isWet = computed(() => sceneInfo.value.scene === 'rain' || sceneInfo.value.scene === 'snow')
/** 雾、阴、降水都会遮住星星 */
const starrySky = computed(() => sceneInfo.value.scene === 'clear' || sceneInfo.value.scene === 'wind')
const showClouds = computed(() => sceneInfo.value.scene !== 'clear')

const rootVars = computed(() => ({
  '--wx-tilt': `${sceneInfo.value.tilt}deg`,
  '--wx-rain-x': `${Math.round(Math.tan((sceneInfo.value.tilt * Math.PI) / 180) * 440)}px`,
  '--wx-drift': `${sceneInfo.value.driftSeconds}s`,
  '--wx-cloud-opacity': sceneInfo.value.cloudOpacity
}))

/** 固定种子的伪随机：粒子分布稳定，不会每次重绘都跳位 */
function rand(seed) {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453
  return x - Math.floor(x)
}

const drops = computed(() =>
  Array.from({ length: sceneInfo.value.particles }, (_, i) => ({
    id: i,
    style: {
      left: `${(rand(i + 1) * 100).toFixed(2)}%`,
      height: `${(12 + rand(i + 7) * 14).toFixed(1)}px`,
      opacity: (0.45 + rand(i + 13) * 0.45).toFixed(2),
      animationDelay: `${(-rand(i + 19) * 2.4).toFixed(2)}s`,
      animationDuration: `${(0.5 + rand(i + 23) * 0.7).toFixed(2)}s`
    }
  }))
)

const flakes = computed(() =>
  Array.from({ length: sceneInfo.value.particles }, (_, i) => {
    const sway = 8 + rand(i + 5) * 22
    return {
      id: i,
      style: {
        left: `${(rand(i + 1) * 100).toFixed(2)}%`,
        width: `${(4.5 + rand(i + 9) * 3.5).toFixed(1)}px`,
        height: `${(4.5 + rand(i + 9) * 3.5).toFixed(1)}px`,
        '--sway': `${sway.toFixed(1)}px`,
        '--flake-alpha': (0.62 + rand(i + 15) * 0.33).toFixed(2),
        animationDelay: `${(-rand(i + 27) * 9).toFixed(2)}s`,
        animationDuration: `${(6 + rand(i + 33) * 6).toFixed(2)}s`
      }
    }
  })
)

const stars = computed(() =>
  Array.from({ length: 20 }, (_, i) => ({
    id: i,
    style: {
      left: `${(rand(i + 41) * 96).toFixed(2)}%`,
      top: `${(rand(i + 47) * 52).toFixed(2)}%`,
      animationDelay: `${(-rand(i + 53) * 4).toFixed(2)}s`,
      animationDuration: `${(2.8 + rand(i + 59) * 2.6).toFixed(2)}s`
    }
  }))
)

const clouds = computed(() =>
  Array.from({ length: 4 }, (_, i) => ({
    id: i,
    style: {
      top: `${[-6, 12, 30, 2][i]}%`,
      left: `${(rand(i + 67) * 90).toFixed(2)}%`,
      width: `${(150 + rand(i + 71) * 130).toFixed(0)}px`,
      animationDelay: `${(-rand(i + 77) * sceneInfo.value.driftSeconds).toFixed(2)}s`,
      animationDuration: `${(sceneInfo.value.driftSeconds * (0.85 + rand(i + 83) * 0.5)).toFixed(2)}s`
    }
  }))
)

const fogBands = computed(() =>
  [
    { top: '26%', delay: '-4s', opacity: 0.62 },
    { top: '54%', delay: '-9s', opacity: 0.5 },
    { top: '76%', delay: '-14s', opacity: 0.42 }
  ].map((b, i) => ({
    id: i,
    style: {
      top: b.top,
      opacity: b.opacity,
      animationDelay: b.delay
    }
  }))
)

const gusts = computed(() => {
  const count = sceneInfo.value.gustLevel === 2 ? 7 : 5
  return Array.from({ length: count }, (_, i) => ({
    id: i,
    style: {
      top: `${(8 + rand(i + 91) * 78).toFixed(2)}%`,
      width: `${(70 + rand(i + 97) * 110).toFixed(0)}px`,
      animationDelay: `${(-rand(i + 103) * 5.5).toFixed(2)}s`,
      animationDuration: `${(4.2 + rand(i + 109) * 2.8).toFixed(2)}s`
    }
  }))
})
</script>

<style scoped>
.wx-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  border-radius: inherit;
  pointer-events: none;
  --wx-cloud: color-mix(in srgb, var(--sky-500) 46%, #93a9ba);
  --wx-rain: rgba(73, 110, 146, 0.72);
  --wx-flake: #ffffff;
  --wx-star: #ffffff;
  --wx-fog: color-mix(in srgb, var(--sky-100) 70%, #ffffff);
  --wx-gust: color-mix(in srgb, var(--brand-500) 42%, #ffffff);
  transition: opacity 600ms var(--ease);
}

/* 深色主题下粒子改冷白，云层降一档，避免糊成一片 */
html.dark .wx-bg {
  --wx-cloud: rgba(196, 214, 226, 0.16);
  --wx-rain: rgba(160, 205, 240, 0.7);
  --wx-fog: rgba(200, 214, 210, 0.18);
  --wx-gust: rgba(169, 214, 191, 0.4);
}

.wx-bg__sky {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(120% 95% at 82% -10%, var(--sky-hi, transparent), transparent 62%),
    linear-gradient(158deg, var(--sky-a, transparent), var(--sky-b, transparent) 64%, transparent);
  transition: background 800ms var(--ease);
}

.wx-bg--idle .wx-bg__sky { opacity: 0.55; }

/* 各场景色调 */
.wx-bg--clear { --sky-a: color-mix(in srgb, var(--gold-500) 15%, transparent); --sky-hi: color-mix(in srgb, var(--gold-500) 20%, transparent); }
.wx-bg--cloudy { --sky-a: color-mix(in srgb, var(--sky-500) 11%, transparent); --sky-hi: color-mix(in srgb, var(--sky-500) 9%, transparent); }
.wx-bg--rain { --sky-a: color-mix(in srgb, var(--sky-700) 17%, transparent); --sky-hi: color-mix(in srgb, var(--sky-700) 20%, transparent); }
.wx-bg--snow { --sky-a: rgba(154, 190, 224, 0.3); --sky-hi: rgba(208, 232, 252, 0.42); }
.wx-bg--fog { --sky-a: rgba(150, 166, 160, 0.16); --sky-hi: rgba(170, 186, 180, 0.14); }
.wx-bg--wind { --sky-a: color-mix(in srgb, var(--brand-500) 11%, transparent); --sky-hi: color-mix(in srgb, var(--sky-500) 9%, transparent); }
.wx-bg--night { --sky-a: color-mix(in srgb, var(--sky-700) 24%, transparent); --sky-hi: color-mix(in srgb, var(--sky-700) 19%, transparent); }
.wx-bg--night.wx-bg--clear { --sky-a: color-mix(in srgb, var(--sky-700) 30%, transparent); --sky-hi: color-mix(in srgb, var(--sky-700) 25%, transparent); }

/*
 * 浅色主题下，夜间/降雨场景铺深色底并改用浅色粒子，
 * 与首页横幅的白字规则配套；深色主题本身已是深底，无需叠加。
 */
html:not(.dark) .wx-bg--night:not(.wx-bg--fog):not(.wx-bg--idle) .wx-bg__sky {
  background: linear-gradient(160deg, rgba(15, 38, 62, 0.84), rgba(29, 56, 84, 0.7) 64%, rgba(38, 68, 98, 0.58));
}
html:not(.dark) .wx-bg--rain:not(.wx-bg--idle) .wx-bg__sky {
  background: linear-gradient(160deg, rgba(33, 60, 86, 0.82), rgba(47, 77, 103, 0.68) 64%, rgba(56, 88, 114, 0.56));
}
html:not(.dark) .wx-bg--night:not(.wx-bg--fog),
html:not(.dark) .wx-bg--rain {
  --wx-cloud: rgba(226, 238, 248, 0.2);
  --wx-rain: rgba(178, 214, 244, 0.82);
}

/* ---- 日 / 月 ---- */
.wx-bg__orb {
  position: absolute;
  top: -40px;
  right: 7%;
  width: 160px;
  height: 160px;
  border-radius: 50%;
  animation: wx-orb 9s ease-in-out infinite;
}
.wx-bg__orb.is-sun {
  background: radial-gradient(circle, rgba(255, 198, 82, 0.7) 0 17%, rgba(255, 198, 82, 0.22) 42%, rgba(255, 198, 82, 0) 70%);
}
.wx-bg__orb.is-sun::after {
  content: '';
  position: absolute;
  inset: -34%;
  border-radius: 50%;
  background: repeating-conic-gradient(from 0deg, rgba(255, 201, 92, 0.09) 0 3deg, transparent 3deg 18deg);
  -webkit-mask: radial-gradient(circle, transparent 0 34%, #000 48%, transparent 71%);
  mask: radial-gradient(circle, transparent 0 34%, #000 48%, transparent 71%);
  animation: wx-spin 70s linear infinite;
}
.wx-bg__orb.is-moon {
  top: -44px;
  right: 30%;
  width: 150px;
  height: 150px;
  background: radial-gradient(circle, rgba(206, 226, 248, 0.2) 0 30%, transparent 64%);
}
/* 用遮罩切出弯月，比整圆更易辨识，也避免和太阳共用同一形态 */
.wx-bg__orb.is-moon::before {
  content: '';
  position: absolute;
  inset: 26%;
  border-radius: 50%;
  background: radial-gradient(circle at 40% 36%, #ffffff, #dbe7f7 72%);
  -webkit-mask: radial-gradient(circle at 70% 32%, transparent 0 48%, #000 50%);
  mask: radial-gradient(circle at 70% 32%, transparent 0 48%, #000 50%);
  filter: drop-shadow(0 0 14px rgba(222, 236, 255, 0.6));
}

@media (max-width: 767px) {
  .wx-bg__orb.is-moon {
    top: -38px;
    right: 8%;
    width: 116px;
    height: 116px;
  }
}

/* ---- 星空 ---- */
.wx-bg__star {
  position: absolute;
  width: 2.5px;
  height: 2.5px;
  border-radius: 50%;
  background: var(--wx-star);
  box-shadow: 0 0 3px rgba(255, 255, 255, 0.8);
  animation: wx-twinkle ease-in-out infinite;
}

/* ---- 云 ---- */
.wx-bg__clouds { position: absolute; inset: 0; }
.wx-bg__cloud {
  position: absolute;
  height: 58px;
  border-radius: 999px;
  background:
    radial-gradient(circle at 20% 72%, var(--wx-cloud) 0 24%, transparent 38%),
    radial-gradient(circle at 42% 48%, var(--wx-cloud) 0 30%, transparent 44%),
    radial-gradient(circle at 62% 40%, var(--wx-cloud) 0 26%, transparent 40%),
    radial-gradient(circle at 78% 68%, var(--wx-cloud) 0 22%, transparent 36%),
    radial-gradient(ellipse at 48% 82%, var(--wx-cloud) 0 34%, transparent 56%);
  filter: blur(3px);
  opacity: var(--wx-cloud-opacity);
  animation: wx-cloud-drift linear infinite;
}

/* ---- 雨 ---- */
.wx-bg__rain { position: absolute; inset: 0; animation: wx-layer-in 600ms ease-out; }
.wx-bg__drop {
  position: absolute;
  top: -16px;
  width: 2px;
  border-radius: 1px;
  background: linear-gradient(to bottom, transparent, var(--wx-rain) 32%);
  transform: rotate(var(--wx-tilt));
  animation: wx-rain-fall linear infinite;
}

/* ---- 雪 ---- */
.wx-bg__snow { position: absolute; inset: 0; animation: wx-layer-in 600ms ease-out; }
.wx-bg__flake {
  position: absolute;
  top: -16px;
  border-radius: 50%;
  background: var(--wx-flake);
  box-shadow: 0 0 3px rgba(84, 124, 164, 0.55), 0 0 1px rgba(84, 124, 164, 0.7);
  opacity: 0.7;
  animation: wx-snow-fall linear infinite;
}

/* ---- 雾 ---- */
.wx-bg__fog {
  position: absolute;
  inset: 0;
  background: linear-gradient(to bottom, transparent 6%, rgba(236, 242, 239, 0.42) 44%, rgba(230, 238, 233, 0.56));
  animation: wx-layer-in 900ms ease-out;
}
html.dark .wx-bg__fog {
  background: linear-gradient(to bottom, transparent 6%, rgba(188, 204, 198, 0.12) 44%, rgba(188, 204, 198, 0.2));
}
.wx-bg__fog-band {
  position: absolute;
  left: -22%;
  width: 144%;
  height: 46px;
  border-radius: 50%;
  background: radial-gradient(ellipse at center, var(--wx-fog) 0 32%, transparent 72%);
  filter: blur(9px);
  animation: wx-fog-drift 17s ease-in-out infinite alternate;
}

/* ---- 风 ---- */
.wx-bg__wind { position: absolute; inset: 0; animation: wx-layer-in 600ms ease-out; }
.wx-bg__gust {
  position: absolute;
  left: 0;
  height: 2px;
  border-radius: 2px;
  background: linear-gradient(90deg, transparent, var(--wx-gust), transparent);
  animation: wx-gust-sweep linear infinite;
}

/* ---- 关键帧 ---- */
@keyframes wx-orb {
  0%, 100% { transform: scale(1); opacity: 0.9; }
  50% { transform: scale(1.06); opacity: 1; }
}
@keyframes wx-spin {
  to { transform: rotate(360deg); }
}
@keyframes wx-twinkle {
  0%, 100% { opacity: 0.25; transform: scale(0.8); }
  50% { opacity: 0.95; transform: scale(1.2); }
}
@keyframes wx-cloud-drift {
  from { transform: translate3d(-240px, 0, 0); }
  to { transform: translate3d(1200px, 0, 0); }
}
@keyframes wx-rain-fall {
  from { transform: translate3d(0, -24px, 0) rotate(var(--wx-tilt)); }
  to { transform: translate3d(var(--wx-rain-x), 440px, 0) rotate(var(--wx-tilt)); }
}
@keyframes wx-snow-fall {
  0% { transform: translate3d(0, -16px, 0); opacity: 0; }
  8% { opacity: var(--flake-alpha); }
  50% { transform: translate3d(var(--sway), 205px, 0); }
  92% { opacity: var(--flake-alpha); }
  100% { transform: translate3d(calc(var(--sway) * -0.5), 430px, 0); opacity: 0; }
}
@keyframes wx-fog-drift {
  from { transform: translate3d(-5%, 0, 0); }
  to { transform: translate3d(5%, 0, 0); }
}
@keyframes wx-gust-sweep {
  0% { transform: translate3d(-180px, 0, 0); opacity: 0; }
  18% { opacity: 0.7; }
  78% { opacity: 0.7; }
  100% { transform: translate3d(1150px, 0, 0); opacity: 0; }
}
@keyframes wx-layer-in {
  from { opacity: 0; }
}
</style>
