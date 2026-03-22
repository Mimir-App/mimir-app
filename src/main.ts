import { createApp } from 'vue';
import { createPinia } from 'pinia';
import { createRouter, createWebHistory } from 'vue-router';
import App from './App.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', component: () => import('./views/DashboardView.vue') },
    { path: '/review', component: () => import('./views/ReviewDayView.vue') },
    { path: '/issues', component: () => import('./views/IssuesView.vue') },
    { path: '/merge-requests', component: () => import('./views/MergeRequestsView.vue') },
    { path: '/discover', component: () => import('./views/DiscoverView.vue') },
    { path: '/timesheets', component: () => import('./views/TimesheetsView.vue') },
    { path: '/settings', component: () => import('./views/SettingsView.vue') },
  ],
});

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount('#app');
