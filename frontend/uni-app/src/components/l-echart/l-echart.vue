<template>
	<canvas 
		v-if="canvasId" 
		class="ec-canvas"
		:id="canvasId" 
		:canvas-id="canvasId" 
		type="2d"
		@touchstart="touchStart" 
		@touchmove="touchMove" 
		@touchend="touchEnd"
	></canvas>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, getCurrentInstance } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
	option: {
		type: Object,
		required: true
	}
})

const emit = defineEmits(['click'])

const canvasId = ref(`ec-canvas-${Date.now()}`)
const ctx = ref<any>(null)
const chart = ref<any>(null)
const instance = getCurrentInstance()

const init = () => {
    console.log('l-echart init called')
	const query = uni.createSelectorQuery().in(instance)
	query.select(`#${canvasId.value}`)
		.fields({ node: true, size: true })
		.exec((res) => {
            console.log('l-echart query result:', res)
			if (!res[0] || !res[0].node) {
                console.error('Canvas node not found')
                return
            }

			const canvas = res[0].node
			const dpr = uni.getSystemInfoSync().pixelRatio
			canvas.width = res[0].width * dpr
			canvas.height = res[0].height * dpr
			
            console.log('Canvas Init Info:', { width: res[0].width, height: res[0].height, dpr })

			const context = canvas.getContext('2d')
			context.scale(dpr, dpr)

			// Manual ECharts Init
			echarts.setCanvasCreator(() => canvas)
			const c = echarts.init(canvas, null, {
				width: res[0].width,
				height: res[0].height,
				devicePixelRatio: dpr
			})
			
			c.setOption(props.option)
			chart.value = c
            console.log('ECharts instance created', c)
            
            // Bind Click event manually if needed or via ZR
            c.on('click', (params: any) => {
                emit('click', params)
            })
		})
}

// Touch handling helper
function wrapTouch(event: any) {
    for (let i = 0; i < event.touches.length; ++i) {
        const touch = event.touches[i]
        touch.offsetX = touch.x
        touch.offsetY = touch.y
    }
    return event
}

const touchStart = (e: any) => {
	if (chart.value && e.touches.length > 0) {
		const touch = e.touches[0]
		const handler = chart.value.getZr().handler
		handler.dispatch('mousedown', {
			zrX: touch.x,
			zrY: touch.y
		})
		handler.dispatch('mousemove', {
			zrX: touch.x,
			zrY: touch.y
		})
		handler.processGesture(wrapTouch(e), 'start')
	}
}

const touchMove = (e: any) => {
	if (chart.value && e.touches.length > 0) {
		const touch = e.touches[0]
		const handler = chart.value.getZr().handler
		handler.dispatch('mousemove', {
			zrX: touch.x,
			zrY: touch.y
		})
		handler.processGesture(wrapTouch(e), 'change')
	}
}

const touchEnd = (e: any) => {
	if (chart.value) {
		const handler = chart.value.getZr().handler
		handler.dispatch('mouseup', {})
		handler.dispatch('click', {})
		handler.processGesture(wrapTouch(e), 'end')
	}
}

watch(() => props.option, (val) => {
	if (chart.value) {
		chart.value.setOption(val)
	}
}, { deep: true })

onMounted(() => {
	// Delay init slightly to ensure node is ready
	setTimeout(() => {
		init()
	}, 100)
})

onBeforeUnmount(() => {
	if (chart.value) {
		chart.value.dispose()
		chart.value = null
	}
})
</script>

<style scoped>
.ec-canvas {
	width: 100%;
	height: 100%;
    display: block;
}
</style>
