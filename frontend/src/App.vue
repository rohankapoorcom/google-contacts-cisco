<script setup lang="ts">
/**
 * Root application component.
 * Wraps all views with the base layout.
 */
import BaseLayout from '@/components/BaseLayout.vue'
</script>

<template>
  <BaseLayout>
    <router-view v-slot="{ Component }">
      <Transition
        mode="out-in"
        enter-active-class="transition duration-200 ease-out"
        enter-from-class="opacity-0 translate-y-1"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition duration-150 ease-in"
        leave-from-class="opacity-100 translate-y-0"
        leave-to-class="opacity-0 -translate-y-1"
      >
        <component :is="Component" />
      </Transition>
    </router-view>
  </BaseLayout>
</template>
