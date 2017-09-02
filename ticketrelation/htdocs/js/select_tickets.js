
import Vue from 'vue';
import relation_single from './relation-single.vue';
import relation_multi from './relation-multi.vue';

window.Vue = Vue;

Vue.component('relation-single', relation_single);
Vue.component('relation-multi', relation_multi);
