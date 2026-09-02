<template>
  <div class="not-found">
    <div class="nf-icon">404</div>
    <h1 class="nf-title">Page not found</h1>
    <p class="nf-desc">The page you are looking for doesn't exist or has been moved.</p>
    <router-link to="/" class="nf-home">Back to Home</router-link>
  </div>
</template>

<style scoped>
.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  padding: 40px 20px;
  text-align: center;
}
.nf-icon {
  font-size: 96px;
  font-weight: 800;
  color: var(--text-muted);
  letter-spacing: -4px;
  opacity: 0.3;
  line-height: 1;
}
.nf-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--text);
  margin: 16px 0 8px;
}
.nf-desc {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 24px;
}
.nf-home {
  padding: 10px 24px;
  border-radius: 8px;
  background: var(--brand);
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  transition: filter .15s;
}
.nf-home:hover {
  filter: brightness(1.1);
}
</style>
