<template>
  <div class="home">
    <!-- 气象横幅：位置 + 大温度 + 一句话农事建议 -->
    <section class="hero" :class="heroTone">
      <div class="hero__left">
        <div class="hero__loc">
          <el-icon :size="14"><LocationInformation /></el-icon>
          <span>{{ location.summary || '定位中…' }}</span>
        </div>
        <div class="hero__main">
          <div class="hero__temp">
            <span class="hero__temp-num num">{{ displayTemp }}</span>
            <span class="hero__temp-unit">°</span>
          </div>
          <div class="hero__meta">
            <div v-if="weatherText" class="hero__cond">{{ weatherText }}</div>
            <div class="hero__sub">
              <span v-if="humidityText">{{ humidityText }}</span>
              <span v-if="windText"> · {{ windText }}</span>
            </div>
          </div>
        </div>
      </div>
      <div class="hero__tip">
        <div class="hero__tip-label">🌾 今日农事建议</div>
        <div class="hero__tip-text">{{ todayAdvice }}</div>
      </div>

      <!-- 模拟数据提示：气象 API 未配置或请求失败降级时给出 -->
      <div v-if="weather.isMock" class="hero__mock">
        <el-icon :size="12"><WarningFilled /></el-icon>
        <span>当前为模拟气象数据（未接入实时气象），仅供参考</span>
      </div>
    </section>

    <!-- 对话主入口 -->
    <section class="ask">
      <div class="ask__avatar">🌱</div>
      <h1 class="ask__title">今天地里该干点啥？</h1>
      <p class="ask__sub">问我天气、病虫害、施肥、品种选择，按你的地块和作物给建议</p>

      <button type="button" class="ask__box" @click="gotoChat()">
        <span class="ask__placeholder">问点什么，比如：玉米现在该不该追肥？</span>
        <span class="ask__send">
          <el-icon :size="18"><Promotion /></el-icon>
        </span>
      </button>

      <div class="ask__chips">
        <button
          v-for="q in quickQuestions"
          :key="q.q"
          type="button"
          class="ask__chip"
          @click="gotoChat(q.q)"
        >
          <span class="ask__chip-emoji">{{ q.emoji }}</span>
          <span>{{ q.label }}</span>
        </button>
      </div>
    </section>

    <!-- 7 天预报小卡片 -->
    <section class="week">
      <div class="week__head">
        <h2 class="week__title">未来 7 天</h2>
        <span class="week__hint">点卡片看农事适宜度</span>
      </div>
      <div class="week__grid">
        <template v-if="weather.available && weather.daily7.length">
          <button
            v-for="(d, i) in weather.daily7"
            :key="i"
            type="button"
            class="week__card"
            :class="{ 'is-active': i === 0 }"
            @click="gotoDay()"
          >
            <span class="week__day">{{ d.label }}</span>
            <span class="week__icon">{{ weatherIcon(d) }}</span>
            <span class="week__temp num">{{ dayTemp(d) }}°</span>
            <span class="week__bar" :style="{ background: suitabilityColor(d) }"></span>
          </button>
        </template>
        <SkeletonCard v-else v-for="i in 7" :key="'sk'+i" variant="card" />
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useWeatherStore } from '@/stores/weather'
import { useLocationStore } from '@/stores/location'
import { useFarmStore } from '@/stores/farm'
import { OPERATIONS, scoreDay } from '@/utils/suitability'
import { suitabilityMeta } from '@/utils/risk'
import { beaufortLevel, normalizeWindDirection } from '@/utils/format'
import SkeletonCard from '@/components/SkeletonCard.vue'

const router = useRouter()
const weather = useWeatherStore()
const location = useLocationStore()
const farm = useFarmStore()

onMounted(() => {
  if (!weather.available && !weather.loading) weather.loadWeather(168)
  if (!farm.fields.length) farm.loadFields()
})

function pick(key) {
  if (!weather.available) return null
  const v = Number(weather.current?.[key])
  return Number.isFinite(v) ? v : null
}
const temperature = computed(() => pick('temperature'))
const humidity = computed(() => pick('humidity'))
const displayTemp = computed(() =>
  temperature.value === null ? '--' : Math.round(temperature.value)
)
/** 湿度取整：气象源给的是 45.262604 这类原始浮点，直接渲染会很难看 */
const humidityText = computed(() =>
  humidity.value === null ? '' : `湿度 ${Math.round(humidity.value)}%`
)
const weatherText = computed(() => {
  if (!weather.available) return '数据加载中'
  // 中科天机当前订阅只给 ws10m/t2m/rh2m/psz/tp，没有天气现象字段：
  // 拿不到就留空（由 v-if 收起这一行），不要显示占位的 '--'
  return weather.current?.text || weather.current?.condition || ''
})
const windText = computed(() => {
  if (!weather.available) return ''
  const cur = weather.current || {}
  const dir = normalizeWindDirection(cur.wind_direction || cur.windDir)
  const mps = Number(cur.wind_speed ?? cur.windSpeed)
  // 接口给的是 m/s，须换算成风级再拼"级"，否则显示成"1.4496349级"
  const level = Number.isFinite(mps) ? beaufortLevel(mps) : null
  return [dir, level === null ? '' : `风力${level}级`].filter(Boolean).join(' ')
})

const heroTone = computed(() => {
  const t = temperature.value
  if (t === null) return 'hero--default'
  if (t >= 28) return 'hero--hot'
  if (t <= 5) return 'hero--cold'
  return 'hero--default'
})

const todayAdvice = computed(() => {
  // 三种"没有建议"的原因分别给出准确文案：加载中 / 服务不可用 / 样本不足，
  // 不再一律说"加载中"（之前因此看起来像永远卡住）
  if (!weather.available) {
    return weather.error ? '气象服务暂不可用，无法生成今日农事建议' : '气象数据加载中…'
  }
  const day = weather.daily7[0]
  if (!day) return '暂无今日气象数据，无法生成农事建议'
  const scores = OPERATIONS.map((op) => scoreDay(op, day).score).filter((s) => Number.isFinite(s))
  if (!scores.length) return '今日预报样本不足，暂无法评估农事适宜度'
  const avg = scores.reduce((a, b) => a + b, 0) / scores.length
  const meta = suitabilityMeta(avg)
  if (meta.level === 'good') return `今日综合适宜度高，气温 ${displayTemp.value}°，适合田间作业与追肥。`
  if (meta.level === 'ok') return `今日条件尚可，${displayTemp.value}°，可择机安排农事，注意天气变化。`
  if (meta.level === 'care') return `今日部分农事受限，${displayTemp.value}°，建议减少户外作业，查看下方预报择期安排。`
  return `今日气象条件不佳，${displayTemp.value}°，不宜开展田间作业，注意防护。`
})

const quickQuestions = [
  { emoji: '🌧️', label: '明天能下地吗', q: '未来三天天气适合下地干活吗？' },
  { emoji: '🌾', label: '玉米追肥用量', q: '玉米现在该不该追肥？追多少？' },
  { emoji: '🐛', label: '大豆虫害怎么防', q: '大豆近期有什么病虫害风险？怎么防？' },
  { emoji: '📋', label: '选什么品种', q: '我们这地块种什么品种好？' }
]

function gotoChat(q) {
  if (q) router.push({ path: '/chat', query: { q } })
  else router.push('/chat')
}
function gotoDay() {
  router.push('/calendar')
}
function weatherIcon(d) {
  const t = (d?.text || d?.condition || '').toString()
  if (/雨|雷/.test(t)) return '🌧️'
  if (/云|阴/.test(t)) return '⛅'
  if (/晴/.test(t)) return '☀️'
  if (/雪/.test(t)) return '❄️'
  // 气象源未提供天气现象字段：只用实测降水（precipSum）兜底，不臆测晴/云
  const p = Number(d?.precipSum)
  if (Number.isFinite(p) && p >= 0.1) return '🌧️'
  return '🌡️'
}
function dayTemp(d) {
  // 按日聚合后的字段名是 tempMax（此前误取 temp_max/temperature/temp，导致 7 天卡片全是 '--°'）
  const t = d?.tempMax ?? d?.temp_max ?? d?.temperature ?? d?.temp
  return Number.isFinite(Number(t)) ? Math.round(Number(t)) : '--'
}
function suitabilityColor(d) {
  const scores = OPERATIONS.map((op) => scoreDay(op, d).score).filter((s) => Number.isFinite(s))
  if (!scores.length) return 'var(--border-strong)'
  const avg = scores.reduce((a, b) => a + b, 0) / scores.length
  const meta = suitabilityMeta(avg)
  const map = { good: 'var(--state-success)', ok: 'var(--state-info)', care: 'var(--state-warning)', bad: 'var(--state-danger)' }
  return map[meta.level] || 'var(--state-success)'
}
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  gap: var(--sp-6);
  max-width: 1100px;
  margin: 0 auto;
  padding: var(--sp-5) var(--sp-6);
}

/* ---- 气象横幅 ---- */
.hero {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  gap: var(--sp-5);
  padding: var(--sp-6) var(--sp-7);
  border-radius: 24px;
  background: linear-gradient(135deg, color-mix(in srgb, var(--brand-500) 12%, var(--bg-card)), var(--bg-card));
  border: 1px solid var(--border-light);
  box-shadow: var(--shadow-2);
}
.hero--hot { background: linear-gradient(135deg, color-mix(in srgb, var(--state-orange) 14%, var(--bg-card)), var(--bg-card)); }
.hero--cold { background: linear-gradient(135deg, color-mix(in srgb, var(--state-info) 14%, var(--bg-card)), var(--bg-card)); }

.hero__loc {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-sm);
  color: var(--text-secondary);
}
.hero__main {
  display: flex;
  align-items: baseline;
  gap: var(--sp-4);
  margin-top: var(--sp-2);
}
.hero__temp-num {
  font-size: 72px;
  font-weight: 200;
  line-height: 1;
  letter-spacing: -3px;
  color: var(--text-title);
}
.hero__temp-unit {
  font-size: 28px;
  font-weight: 300;
  color: var(--text-secondary);
  margin-left: -8px;
}
.hero__cond {
  font-size: var(--fs-h3);
  font-weight: 600;
  color: var(--text-title);
}
.hero__sub {
  font-size: var(--fs-sm);
  color: var(--text-secondary);
  margin-top: 2px;
}

.hero__tip {
  max-width: 340px;
  background: color-mix(in srgb, var(--brand-500) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--brand-500) 24%, transparent);
  border-radius: 16px;
  padding: var(--sp-4) var(--sp-5);
  align-self: center;
}
.hero__tip-label {
  font-size: var(--fs-caption);
  color: var(--brand-600);
  margin-bottom: 4px;
}
.hero__tip-text {
  font-size: var(--fs-body);
  color: var(--text-body);
  line-height: 1.5;
}
.hero__mock {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  font-size: var(--fs-caption);
  color: var(--state-warning);
  background: color-mix(in srgb, var(--state-warning) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--state-warning) 26%, transparent);
  border-radius: 10px;
  padding: var(--sp-1) var(--sp-2);
  margin-top: var(--sp-3);
  flex-basis: 100%;
}

/* ---- 对话主入口 ---- */
.ask {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--sp-7) 0 var(--sp-5);
}
.ask__avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--brand-400), var(--brand-600));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  box-shadow: var(--shadow-brand);
  margin-bottom: var(--sp-3);
}
.ask__title {
  font-size: var(--fs-h1);
  font-weight: 600;
  color: var(--text-title);
  margin: 0 0 var(--sp-2);
  text-align: center;
}
.ask__sub {
  font-size: var(--fs-body);
  color: var(--text-secondary);
  margin: 0 0 var(--sp-6);
  text-align: center;
}
.ask__box {
  width: 100%;
  max-width: 680px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: 24px;
  padding: var(--sp-4) var(--sp-5);
  box-shadow: var(--shadow-2);
  cursor: text;
  transition: border-color var(--dur-fast) var(--ease), box-shadow var(--dur-fast) var(--ease);
}
.ask__box:hover {
  border-color: var(--brand-400);
  box-shadow: var(--shadow-brand);
}
.ask__placeholder {
  flex: 1;
  color: var(--text-disabled);
  font-size: var(--fs-body-lg);
  text-align: left;
}
.ask__send {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--brand-400), var(--brand-600));
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ask__chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  justify-content: center;
  margin-top: var(--sp-4);
  max-width: 680px;
}
.ask__chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  color: var(--text-body);
  padding: var(--sp-2) var(--sp-4);
  border-radius: 999px;
  font-size: var(--fs-sm);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
}
.ask__chip:hover {
  border-color: var(--brand-400);
  color: var(--brand-600);
  background: color-mix(in srgb, var(--brand-500) 6%, var(--bg-card));
}
.ask__chip-emoji { font-size: 14px; }

/* ---- 7 天预报 ---- */
.week__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: var(--sp-3);
}
.week__title {
  font-size: var(--fs-h3);
  font-weight: 600;
  color: var(--text-title);
  margin: 0;
}
.week__hint {
  font-size: var(--fs-caption);
  color: var(--text-disabled);
}
.week__grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: var(--sp-2);
}
.week__card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-radius: 16px;
  padding: var(--sp-3) var(--sp-1);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease);
}
.week__card:hover { border-color: var(--brand-400); }
.week__card.is-active {
  border-color: var(--brand-500);
  box-shadow: var(--shadow-brand);
}
.week__day {
  font-size: var(--fs-caption);
  color: var(--text-secondary);
}
.week__icon { font-size: 22px; line-height: 1; }
.week__temp {
  font-size: var(--fs-h4);
  font-weight: 600;
  color: var(--text-title);
}
.week__bar {
  width: 24px;
  height: 4px;
  border-radius: 2px;
  margin-top: 2px;
}

/* ---- 响应式 ---- */
@media (max-width: 767px) {
  .home { padding: var(--sp-4) var(--gutter-mobile); gap: var(--sp-5); }
  .hero { flex-direction: column; padding: var(--sp-5); }
  .hero__tip { max-width: 100%; }
  .hero__temp-num { font-size: 56px; }
  .ask { padding: var(--sp-6) 0 var(--sp-4); }
  .ask__title { font-size: var(--fs-h2); }
  .week__grid { grid-template-columns: repeat(4, 1fr); }
}
</style>
