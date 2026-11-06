/**
 * 作物动画数据层（纯数据，无 DOM）
 * --------------------------------------------------------------------------
 * 22 种作物归到 8 个形态族，每个族给出 6 个可视化阶段的轮廓参数。
 * CropScene 只负责把这些数字画成 SVG；这里不关心怎么画，方便单测。
 *
 * 阶段划分与后端物候期不是一一对应（后端起止更多、更细），
 * 只取「看得出形态变化」的 6 段：播种出苗 → 苗期 → 旺长 → 开花抽穗 → 灌浆结果 → 成熟。
 */
import { cropName } from './growth'

export const VISUAL_STAGES = [
  { key: 'sowing', label: '播种出苗' },
  { key: 'seedling', label: '苗期' },
  { key: 'growing', label: '旺长' },
  { key: 'flowering', label: '开花抽穗' },
  { key: 'fruiting', label: '灌浆结果' },
  { key: 'mature', label: '成熟' }
]

/** 形态族：sway 为自然摆动的幅度（px）与周期（s） */
export const MORPHOLOGY_FAMILIES = {
  tall_grass: { label: '高秆禾本', swayAmp: 1.6, swaySpeed: 3.6 },
  dense_grass: { label: '密植禾本', swayAmp: 1.2, swaySpeed: 4.2 },
  legume: { label: '豆类', swayAmp: 0.9, swaySpeed: 4.6 },
  tuber: { label: '根茎', swayAmp: 0.7, swaySpeed: 5.0 },
  rosette_leaf: { label: '叶菜莲座', swayAmp: 0.5, swaySpeed: 5.4 },
  solanaceous: { label: '茄果瓜类', swayAmp: 1.0, swaySpeed: 4.0 },
  woody: { label: '木本藤本', swayAmp: 0.45, swaySpeed: 6.0 },
  flower: { label: '花卉多肉', swayAmp: 0.6, swaySpeed: 5.2 }
}

export const CROP_MORPHOLOGY = {
  玉米: 'tall_grass',
  小麦: 'dense_grass',
  水稻: 'dense_grass',
  莜麦: 'dense_grass',
  大豆: 'legume',
  马铃薯: 'tuber',
  胡萝卜: 'tuber',
  白菜: 'rosette_leaf',
  菠菜: 'rosette_leaf',
  番茄: 'solanaceous',
  黄瓜: 'solanaceous',
  辣椒: 'solanaceous',
  苹果: 'woody',
  梨: 'woody',
  桃: 'woody',
  葡萄: 'woody',
  柑橘: 'woody',
  月季: 'flower',
  菊花: 'flower',
  百合: 'flower',
  兰花: 'flower',
  多肉植物: 'flower'
}

/**
 * 各阶段轮廓：height/width 为相对场景（0~1）的占比，
 * leaves 为可画叶片数，flower/fruit 决定该阶段画不画花/果。
 */
const STAGE_SHAPE = {
  tall_grass: {
    height: [0.12, 0.30, 0.66, 0.92, 0.95, 0.88],
    width: [0.05, 0.12, 0.26, 0.30, 0.30, 0.26],
    leaves: [2, 3, 6, 6, 5, 4],
    flower: [false, false, false, true, false, false],
    fruit: [false, false, false, false, true, true]
  },
  dense_grass: {
    height: [0.10, 0.24, 0.55, 0.82, 0.86, 0.80],
    width: [0.06, 0.12, 0.24, 0.28, 0.30, 0.30],
    leaves: [3, 4, 6, 6, 5, 4],
    flower: [false, false, false, true, false, false],
    fruit: [false, false, false, false, true, true]
  },
  legume: {
    height: [0.10, 0.22, 0.48, 0.62, 0.62, 0.56],
    width: [0.08, 0.14, 0.28, 0.34, 0.34, 0.30],
    leaves: [2, 4, 7, 6, 5, 4],
    flower: [false, false, false, true, false, false],
    fruit: [false, false, false, false, true, true]
  },
  tuber: {
    height: [0.08, 0.22, 0.45, 0.48, 0.46, 0.40],
    width: [0.08, 0.16, 0.30, 0.32, 0.30, 0.26],
    leaves: [2, 4, 6, 6, 5, 3],
    flower: [false, false, false, true, false, false],
    fruit: [false, false, false, false, true, true]
  },
  rosette_leaf: {
    height: [0.10, 0.24, 0.42, 0.52, 0.56, 0.50],
    width: [0.10, 0.20, 0.32, 0.36, 0.38, 0.34],
    leaves: [3, 5, 8, 7, 8, 6],
    flower: [false, false, false, true, false, false],
    fruit: [false, false, false, false, true, true]
  },
  solanaceous: {
    height: [0.10, 0.26, 0.58, 0.72, 0.74, 0.66],
    width: [0.08, 0.16, 0.26, 0.30, 0.32, 0.28],
    leaves: [3, 5, 8, 7, 6, 4],
    flower: [false, false, false, true, false, false],
    fruit: [false, false, false, false, true, true]
  },
  woody: {
    height: [0.12, 0.30, 0.62, 0.74, 0.76, 0.70],
    width: [0.06, 0.14, 0.30, 0.36, 0.38, 0.34],
    leaves: [2, 4, 8, 7, 7, 5],
    flower: [false, false, false, true, false, false],
    fruit: [false, false, false, false, true, true]
  },
  flower: {
    height: [0.08, 0.22, 0.46, 0.58, 0.58, 0.52],
    width: [0.08, 0.16, 0.28, 0.32, 0.30, 0.26],
    leaves: [2, 4, 6, 5, 5, 4],
    flower: [false, false, false, true, true, false],
    fruit: [false, false, false, false, false, true]
  }
}

const FAMILY_PALETTE = {
  tall_grass: {
    stem: 'var(--brand-700)', leaf: 'var(--brand-500)',
    accent: '#f2d97a', fruit: 'var(--gold-500)',
    dryLeaf: 'var(--gold-500)', dryStem: 'var(--gold-700)'
  },
  dense_grass: {
    stem: 'var(--brand-600)', leaf: 'var(--state-success)',
    accent: '#efe2b0', fruit: 'var(--gold-500)',
    dryLeaf: 'var(--gold-500)', dryStem: 'var(--gold-700)'
  },
  legume: {
    stem: 'var(--brand-600)', leaf: 'var(--brand-500)',
    accent: '#f3ecd0', fruit: 'var(--gold-700)',
    dryLeaf: 'var(--gold-500)', dryStem: 'var(--gold-700)'
  },
  tuber: {
    stem: 'var(--brand-700)', leaf: 'var(--brand-500)',
    accent: '#f0dfe9', fruit: '#c98a4b',
    dryLeaf: 'var(--gold-500)', dryStem: 'var(--gold-700)'
  },
  rosette_leaf: {
    stem: 'var(--brand-600)', leaf: 'var(--brand-400)',
    accent: '#f6e6a0', fruit: 'var(--brand-300)',
    dryLeaf: 'var(--gold-500)', dryStem: 'var(--gold-700)'
  },
  solanaceous: {
    stem: 'var(--brand-700)', leaf: 'var(--brand-600)',
    accent: '#fff0be', fruit: 'var(--state-danger)',
    dryLeaf: 'var(--state-orange)', dryStem: 'var(--gold-700)'
  },
  woody: {
    stem: '#7a5a3a', leaf: 'var(--brand-500)',
    accent: '#fbe3e8', fruit: 'var(--state-danger)',
    dryLeaf: 'var(--state-orange)', dryStem: '#6b4d31'
  },
  flower: {
    stem: 'var(--brand-600)', leaf: 'var(--brand-500)',
    accent: 'var(--state-purple)', fruit: 'var(--state-warning)',
    dryLeaf: 'var(--gold-500)', dryStem: 'var(--gold-700)'
  }
}

/** 单作物色偏（同族作物一眼能区分：梨果偏金、葡萄偏紫、柑橘偏橙…） */
const CROP_TINT = {
  小麦: { leaf: 'var(--state-success)' },
  莜麦: { leaf: 'var(--state-success)' },
  水稻: { leaf: 'var(--state-success)', fruit: 'var(--gold-500)' },
  马铃薯: { accent: '#efe0f0' },
  番茄: { fruit: 'var(--state-danger)' },
  黄瓜: { fruit: 'var(--brand-400)' },
  辣椒: { fruit: 'var(--state-danger)' },
  苹果: { fruit: 'var(--state-danger)' },
  梨: { fruit: 'var(--gold-500)' },
  桃: { fruit: 'var(--state-orange)' },
  葡萄: { fruit: 'var(--state-purple)' },
  柑橘: { fruit: 'var(--state-orange)' },
  月季: { accent: 'var(--state-danger)' },
  菊花: { accent: 'var(--gold-500)' },
  百合: { accent: '#f3c9d6' },
  兰花: { accent: 'var(--state-purple)' },
  多肉植物: { accent: 'var(--brand-300)' }
}

/** 阶段名 → 可视化阶段下标；先判成熟/结果/开花，再往下退，避免子串误命中 */
const STAGE_KEYWORDS = [
  [/成熟|收获|采收/, 5],
  [/灌浆|鼓粒|块茎|淀粉|膨大|结球|肉质根|坐果|结荚|结果|上色|吐丝/, 4],
  [/抽雄|抽穗|孕穗|开花|现蕾|抽薹/, 3],
  [/拔节|伸蔓|定植|分枝|旺长|返青|新芽|莲座|叶丛|生长期|分蘖|三叶/, 2],
  // 必须在「苗期」之前：「出苗期」包含「苗期」子串，否则会被误判成苗期
  [/播种|出苗|秧苗|萌芽/, 0],
  [/苗期|越冬|幼苗/, 1]
]

function clamp(v, lo, hi) {
  return Math.min(hi, Math.max(lo, v))
}

/**
 * 阶段名 → 可视化阶段下标。
 * @param {string} name 后端/表单里的阶段名
 * @returns {number|null} 无法识别返回 null
 */
export function stageFromName(name) {
  const s = String(name || '')
  if (!s) return null
  for (const [re, idx] of STAGE_KEYWORDS) if (re.test(s)) return idx
  return null
}

/**
 * 解析可视化阶段，优先级：
 * 表单阶段名 → 生长模型当前阶段 → 模型连续进度 → 折中值 3（旺长偏后）。
 * @param {{ stage?:string, growth?:Object }} [input]
 * @returns {number} 0~5
 */
export function resolveVisualStage(input = {}) {
  const direct = stageFromName(input.stage)
  if (direct !== null) return direct

  const growth = input.growth
  if (growth) {
    if (growth.harvested) return VISUAL_STAGES.length - 1
    const fromModel = stageFromName(growth.currentStage)
    if (fromModel !== null) return fromModel
    const frac = Number(growth.currentFrac)
    if (Number.isFinite(frac)) {
      return Math.min(VISUAL_STAGES.length - 1, Math.floor(clamp(frac, 0, 0.9999) * VISUAL_STAGES.length))
    }
  }
  return 3
}

/** 稳定的 0~1 伪随机：同一地块的摆动相位固定，避免每次渲染跳一下 */
export function hash01(str) {
  const s = String(str ?? '')
  let h = 2166136261
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return ((h >>> 0) % 1000) / 1000
}

/**
 * 生成组件所需的完整绘制参数。
 * @param {string} crop 作物名（含别称）
 * @param {{ stage?:string, growth?:Object, seed?:string }} [opts]
 * @returns {Object}
 */
export function getCropVisual(crop, opts = {}) {
  const name = cropName(crop) || String(crop || '').trim() || '作物'
  const family = CROP_MORPHOLOGY[name] || 'rosette_leaf'
  const stage = resolveVisualStage({ stage: opts.stage, growth: opts.growth })
  const shape = STAGE_SHAPE[family]
  const palette = { ...FAMILY_PALETTE[family], ...(CROP_TINT[name] || {}) }
  const mature = stage === VISUAL_STAGES.length - 1
  const sway = MORPHOLOGY_FAMILIES[family]
  const seed = opts.seed || name

  return {
    crop: name,
    family,
    familyLabel: sway.label,
    stage,
    stageKey: VISUAL_STAGES[stage].key,
    stageLabel: VISUAL_STAGES[stage].label,
    height: shape.height[stage],
    width: shape.width[stage],
    leafCount: shape.leaves[stage],
    flowering: shape.flower[stage],
    fruiting: shape.fruit[stage],
    mature,
    colors: {
      stem: mature ? palette.dryStem : palette.stem,
      leaf: mature ? palette.dryLeaf : palette.leaf,
      accent: palette.accent,
      fruit: palette.fruit,
      soil: '#7a5a3a',
      soilDark: '#62452c'
    },
    sway: { amp: sway.swayAmp, speed: sway.swaySpeed, phase: hash01(seed) }
  }
}
