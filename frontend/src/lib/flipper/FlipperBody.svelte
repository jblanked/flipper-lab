<script lang="ts">
  import { bindScreenCanvas } from '$lib/flipper/store.svelte';

  let { flipperName = 'Flipper', flipperColor = '2', screenScale = 1 }: {
    flipperName?: string;
    flipperColor?: string;
    screenScale?: number;
  } = $props();

  // device reports color as a number string: 1 = black, 3 = transparent, else white
  let bodyClass = $derived(
    flipperColor === '1' ? 'body-black' :
    flipperColor === '3' ? 'body-transparent' : 'body-white'
  );

  // hand our screen canvas to the store so the stream renders into it
  let canvas = $state<HTMLCanvasElement | undefined>();
  $effect(() => {
    if (canvas) bindScreenCanvas(canvas);
  });
</script>

<div class="flipper-wrap">
  <h5 class="flipper-name text-bold">{flipperName}</h5>
  <div class="flipper {bodyClass}">
    <div class="flipper__display" style="width:{128 * screenScale}px; height:{64 * screenScale}px;">
      <!-- canvas stays at native 128×64 res; CSS scales the display -->
      <canvas bind:this={canvas} width="128" height="64" style="image-rendering: pixelated;"></canvas>
    </div>
  </div>
</div>
