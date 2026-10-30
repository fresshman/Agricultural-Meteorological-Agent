<template>
  <div class="session-list">
    <div class="session-list__head">
      <el-button type="primary" class="session-list__new" @click="emit('new')">
        <el-icon><Plus /></el-icon>
        <span>新建会话</span>
      </el-button>
      <el-input
        v-model="keyword"
        class="session-list__search"
        placeholder="搜索会话"
        clearable
        size="default"
        aria-label="搜索会话"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <div class="session-list__body">
      <EmptyState
        v-if="!filtered.length"
        icon="ChatDotSquare"
        :title="keyword ? '没有匹配的会话' : '还没有会话'"
        :description="keyword ? '换个关键词试试' : '点击上方「新建会话」开始一次农事咨询'"
        size="sm"
      />

      <template v-else>
        <section v-for="group in groups" :key="group.label" class="session-group">
          <h4 class="session-group__label">{{ group.label }}</h4>
          <ul class="session-group__list">
            <li
              v-for="session in group.items"
              :key="session.id"
              class="session-item"
              :class="{ 'is-active': session.id === currentId }"
            >
              <button
                type="button"
                class="session-item__main"
                :aria-current="session.id === currentId"
                @click="emit('select', session.id)"
              >
                <el-icon :size="15" class="session-item__icon"><ChatDotSquare /></el-icon>
                <span v-if="editingId !== session.id" class="session-item__title truncate">
                  {{ session.title || '未命名会话' }}
                </span>
                <el-input
                  v-else
                  :ref="(el) => setEditRef(el, session.id)"
                  v-model="editingTitle"
                  class="session-item__input"
                  size="small"
                  maxlength="40"
                  @click.stop
                  @keyup.enter="commitRename"
                  @blur="commitRename"
                />
                <span class="session-item__meta num">{{ (session.messages || []).length }}</span>
              </button>

              <el-dropdown trigger="click" placement="bottom-end" @command="(cmd) => onCommand(cmd, session)">
                <button type="button" class="session-item__more" aria-label="会话操作">
                  <el-icon :size="14"><MoreFilled /></el-icon>
                </button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="rename">
                      <el-icon><EditPen /></el-icon>
                      <span>重命名</span>
                    </el-dropdown-item>
                    <el-dropdown-item command="remove" divided>
                      <el-icon><Delete /></el-icon>
                      <span>删除</span>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </li>
          </ul>
        </section>
      </template>
    </div>

    <footer class="session-list__foot">
      <span class="num">{{ sessions.length }}</span>
      <span>个会话 · 本地保存</span>
    </footer>
  </div>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import EmptyState from '@/components/EmptyState.vue'
import { dayGroupLabel } from '@/utils/format'

const props = defineProps({
  /** 全部会话（updatedAt 倒序） */
  sessions: { type: Array, default: () => [] },
  /** 当前会话 id */
  currentId: { type: String, default: null }
})

const emit = defineEmits(['select', 'new', 'rename', 'remove'])

const keyword = ref('')
const editingId = ref('')
const editingTitle = ref('')
const editRefs = new Map()

function setEditRef(el, id) {
  if (el) editRefs.set(id, el)
  else editRefs.delete(id)
}

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return props.sessions
  return props.sessions.filter((session) => {
    const title = String(session.title || '').toLowerCase()
    const hitTitle = title.includes(kw)
    const hitMessage = (session.messages || []).some((m) =>
      String(m?.content || '').toLowerCase().includes(kw)
    )
    return hitTitle || hitMessage
  })
})

/** 按 今天 / 昨天 / 更早 分组 */
const groups = computed(() => {
  const order = ['今天', '昨天', '更早']
  const map = new Map(order.map((label) => [label, []]))
  for (const session of filtered.value) {
    const label = dayGroupLabel(session.updatedAt || session.createdAt)
    if (!map.has(label)) map.set(label, [])
    map.get(label).push(session)
  }
  return order
    .map((label) => ({ label, items: map.get(label) || [] }))
    .filter((group) => group.items.length)
})

async function startRename(session) {
  editingId.value = session.id
  editingTitle.value = session.title || ''
  await nextTick()
  const input = editRefs.get(session.id)
  input?.focus?.()
  input?.select?.()
}

function commitRename() {
  if (!editingId.value) return
  const id = editingId.value
  const title = editingTitle.value
  editingId.value = ''
  if (String(title || '').trim()) emit('rename', id, title.trim())
}

async function onCommand(command, session) {
  if (command === 'rename') {
    await startRename(session)
    return
  }
  if (command === 'remove') {
    try {
      await ElMessageBox.confirm(
        `确定删除会话「${session.title || '未命名会话'}」？删除后无法恢复。`,
        '删除会话',
        { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
      )
      emit('remove', session.id)
    } catch (err) {
      /* 用户取消 */
    }
  }
}

defineExpose({ formatTime })
</script>

<style scoped>
.session-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--bg-card);
}

.session-list__head {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding: var(--sp-4);
  border-bottom: 1px solid var(--border-light);
}

.session-list__new {
  width: 100%;
}

.session-list__body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding: var(--sp-2) var(--sp-2) var(--sp-4);
}

.session-group {
  margin-top: var(--sp-2);
}

.session-group__label {
  padding: var(--sp-2) var(--sp-2) var(--sp-1);
  font-size: var(--fs-caption);
  font-weight: 600;
  color: var(--text-disabled);
}

.session-group__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.session-item {
  display: flex;
  align-items: center;
  border-radius: var(--radius-md);
  transition: background var(--dur-fast) var(--ease);
}

.session-item:hover {
  background: var(--bg-subtle);
}

.session-item.is-active {
  background: var(--brand-50);
}

html.dark .session-item.is-active {
  background: color-mix(in srgb, var(--brand-500) 14%, transparent);
}

.session-item__main {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  height: 36px;
  padding: 0 var(--sp-2);
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
  color: var(--text-body);
}

.session-item.is-active .session-item__main {
  color: var(--brand-600);
  font-weight: 500;
}

.session-item__icon {
  flex: 0 0 auto;
  color: var(--text-disabled);
}

.session-item.is-active .session-item__icon {
  color: var(--brand-500);
}

.session-item__title {
  flex: 1 1 auto;
  min-width: 0;
  font-size: var(--fs-sm);
}

.session-item__input {
  flex: 1 1 auto;
  min-width: 0;
}

.session-item__meta {
  flex: 0 0 auto;
  font-size: var(--fs-caption);
  color: var(--text-disabled);
}

.session-item__more {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  margin-right: var(--sp-1);
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-disabled);
  cursor: pointer;
  opacity: 0;
  transition: opacity var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease);
}

.session-item:hover .session-item__more,
.session-item__more:focus-visible {
  opacity: 1;
}

.session-item__more:hover {
  color: var(--text-body);
  background: var(--border-light);
}

.session-list__foot {
  display: flex;
  align-items: center;
  gap: var(--sp-1);
  padding: var(--sp-2) var(--sp-4);
  border-top: 1px solid var(--border-light);
  font-size: var(--fs-caption);
  color: var(--text-disabled);
}

@media (max-width: 767px) {
  .session-item__more {
    opacity: 1;
  }
}
</style>
