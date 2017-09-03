
import Vue from 'vue';
import schedule from './schedule.vue';
import scheduleItem from './schedule-item.vue';

window.Vue = Vue;

Vue.component('schedule', schedule);
Vue.component('schedule-item', scheduleItem);

