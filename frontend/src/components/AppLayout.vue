<template>
  <div class="app-layout">
    <nav class="side-nav">
      <router-link to="/wiki">📚 知识库</router-link>
      <router-link to="/ingest">⬆ 摄入</router-link>
      <router-link to="/chat">💬 对话</router-link>
      <router-link to="/private">🔒 私有</router-link>
    </nav>
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
}
.side-nav {
  width: 100px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px 8px;
  border-right: 1px solid #e0e0e0;
}
.side-nav a {
  text-decoration: none;
  font-size: 12px;
  color: #555;
}
.side-nav a.router-link-active {
  color: #1a73e8;
  font-weight: bold;
}
.main-content {
  flex: 1;
  overflow: auto;
  padding: 24px;
}
</style>
