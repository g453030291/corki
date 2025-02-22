// audio-processor.js
class AudioProcessor extends AudioWorkletProcessor {
    constructor() {
        super();
        this.accumulatedData = [];
        this.sampleRate = 16000;
        this.port.onmessage = (event) => {
            if (event.data === 'stop') {
                this.stopProcessing();
            }
        };
    }

    stopProcessing() {
        this.port.postMessage('stopped');
        this.port.close();
    }

    process(inputs, outputs, parameters) {
        const input = inputs[0];
        if (input && input.length > 0) {
            const inputData = input[0];

            // 转换为16位整数
            const pcmData = new Int16Array(inputData.length);
            for (let i = 0; i < inputData.length; i++) {
                pcmData[i] = Math.max(-32768, Math.min(32767, inputData[i] * 0x7FFF));
            }

            // 累积音频数据
            this.accumulatedData.push(...pcmData);

            // 如果累积的数据达到 1 秒（16000 采样点），发送数据
            if (this.accumulatedData.length >= this.sampleRate) {
                const dataToSend = this.accumulatedData.slice(0, this.sampleRate);
                this.port.postMessage(dataToSend);
                this.accumulatedData = this.accumulatedData.slice(this.sampleRate);
            }
        }
        return true;
    }
}

registerProcessor('audio-processor', AudioProcessor);
