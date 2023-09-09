<template>
  <div>
    <h1>DICOM Image Processor</h1>
    <input type="file" name="file" @change="uploadDicomFile" accept=".dcm" />
    <label for="thresholdInput">Threshold:</label>
    <input
      type="number"
      id="thresholdInput"
      v-model="threshold"
      step="0.01"
      min="0"
      max="1"
    />
    <button @click="processImages" :disabled="processing">Process Images</button>
    <p v-if="processing">Processing...</p>
    <p v-if="error">{{ error }}</p>
    <p v-if="result">Volume: {{ result }} mm³</p>
    <img v-if="processedImage !== null" :src="processedImage" alt="Processed Image" />
  </div>
</template>

<script>
import axios from 'axios';

export default {
  data() {
    return {
      dicomFile: null,
      result: null,
      processedImage: null,
      error: null,
      processing: false,
      threshold: 0.5, // Initialize threshold with a default value
    };
  },
  methods: {
    uploadDicomFile(event) {
      this.dicomFile = event.target.files[0];
    },
    processImages() {
      if (!this.dicomFile) {
        this.error = 'Please upload a DICOM image.';
        return;
      }

      this.error = null;
      this.processing = true;

      const formData = new FormData();
      formData.append('file', this.dicomFile);

      // Send the threshold value along with the file
      axios
        .post(`http://localhost:5000/process?threshold=${this.threshold}`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
        .then((response) => {
          console.log(response);
          this.result = response.data.volume_mm3;
        })
        .catch((error) => {
          this.error = 'Error processing images. Please try again.';
          console.error('Error processing images: ', error);
        })
        .finally(() => {
          this.processing = false;
        });
    },
  },
};
</script>

<style>
/* Add your custom styles here */
</style>

