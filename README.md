# Our goal
In this brief project, we develop a simple web-based platform where users can upload a DICOM image. Upon upload, the pixel data of the DICOM should be extracted, normalized, and thresholded. After processing, the system should display the volume (in mm 3 ) of the thresholded pixels. 

Requirements:
1. Web Interface:

• A simple web page with a drop zone for uploading DICOM images.
• Display the number of pixels that are above the threshold once the
processing is complete.
• Although we do not want to spend that much time on the UI
elements, it is important that the interface is functioning as intended.
• We recommend Vue.js

2. Backend:

• REST Endpoints for communicating with the Web interface. All the
endpoints should return JSON data.
• We recommend using the FastAPI Python framework
• Extraction of pixel data from the DICOM (We recommend the
Python package pydicom).
• Normalize the pixel data to a range of [0, 1].
• The pixel data should be thresholded(>). Using the threshold value
specified in the web server’s config file (default to 0.5 if not provided).
• Return the volume of the thresholded pixels in mm

3. Docker:

• We package the application in Docker images.
• We provide Dockerfiles for both backend and frontend
• Ideally, a docker-compose.yml for running the solution.



# System requirements

I assume we have a Linux OS, I tested on my laptop which has "NAME="Linux Mint"
VERSION="20.3 (Una)". We need to have `docker` and `docker-compose` installed on our system so we can make images. My `Docker version 24.0.2, build cb74dfc` and `Docker Compose version v2.17.2`. 

### Without docker

If you would like to not making a docker images you can also create a new conda environment [here](https://conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#) with a stable python version, e.g. "conda create -n myenv python=3.9", and then installing Fastapi [here](https://anaconda.org/conda-forge/fastapi) and Vue [here](https://anaconda.org/conda-forge/vue). To run a fatapi application you need also to use uvicorn [here](https://anaconda.org/conda-forge/uvicorn). 


For non-dockerized version of the application I also tested it on "Ubuntu 20.04" by creating a new conda environment as I mentioned above.

# Running the application
To run this application just navigate to the directory that you download/clone this repository and then open a new terminal and type:

```bash
sudo docker-compose up --build
```
If the docker image is built successefully you can get access to your frontend via ``http://localhost:8080/`` in the browser. Then you can see a page with two buttons one for uploading the `.dcm` picture and the other for makeing request to the backend `process image`. You can also set a threshold value as the input. Doing so you will see the results on the page. 
 

## What is FastAPI?

[FastAPI](https://fastapi.tiangolo.com/) is a modern, batteries-included Python web framework that's perfect for building RESTful APIs. It can handle both synchronous and asynchronous requests and has built-in support for data validation, JSON serialization, authentication and authorization, and OpenAPI documentation.


## What is Vue?

[Vue](https://vuejs.org/) is an open-source JavaScript framework used for building user interfaces. It adopted some of the best practices from React and Angular. That said, compared to React and Angular, it's much more approachable, so beginners can get up and running quickly. It's also just as powerful, so it provides all the features you'll need to create modern front-end applications.



## FastAPI Setup

Start by creating a new project folder called "fastapi-vue" and add the following files and folders:
```
fastapi-vue
├── docker-compose.yml
└── services
    └── backend
        ├── Dockerfile
        ├── requirements.txt
        └── src
            └── main.py
```

The following command will create the project structure:
```bash
$ mkdir fastapi-vue && \
  cd fastapi-vue && \
  mkdir -p services/backend/src && \
  touch docker-compose.yml services/backend/Dockerfile && \
  touch services/backend/requirements.txt services/backend/src/main.py
```

Next, add the following code to services/backend/Dockerfile:

```dockerfile
FROM python:3.8

RUN mkdir app
WORKDIR /app

ENV PATH="${PATH}:/root/.local/bin"
ENV PYTHONPATH=.

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install python-multipart
RUN pip install -r requirements.txt

COPY src/ /app/src/
```

Our final goal is to process a `.dcm` image at the backend, so we need to add the following dependencies to the `services/backend/requirements.txt` file:

```plaintext
fastapi == 0.88.0
uvicorn == 0.20.0
pydicom == 2.*
numpy == 1.*
scipy == 1.*
```
Update docker-compose.yml like so:

```dockerfile
version: '3.8'

services:

  backend:
    build: ./services/backend
    ports:
      - 5000:5000
    volumes:
      - backend-data:/app/results  # Define a named volume 'backend-data' and mount it to /app/results in the container
      - ./local_results:/app/results  # Map a local directory 'local_results' to /app/results in the container
    command: uvicorn src.main:app --reload --host 0.0.0.0 --port 5000

```

Before we build the image, let's add a test route to `services/backend/src/main.py` so we can quickly test that the app was built successfully:

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return "Hello, World!"
```







Build the image in your terminal:

```bash
$ docker-compose up -d --build
```

Once done, navigate to `http://127.0.0.1:5000/` in your browser of choice. You should see:

```plaintext
"Hello, World!"
```

You can view the Swagger UI at `http://localhost:5000/docs`, see also [here](https://fastapi.tiangolo.com/tutorial/first-steps/) for more explanation.


##### `Remark:` If you `do not want to use docker` image and you created a `conda environment` and installed everything as I mentioned earlier, to run the Fastapi application, browse to the directory `/backend/src/main.py` on your machine and run this command on the terminal:  
```bash
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

Before jumping to core of the image processing algorithm, we have to keep in our mind that we have to communicate with our `frontend` application! so we need to modify our `/backend/src/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # NEW


app = FastAPI()

# NEW
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return "Hello, World!"

```

`CORSMiddleware` is required to make [cross-origin](https://en.wikipedia.org/wiki/Cross-origin_resource_sharing) requests -- i.e., requests that originate from a different protocol, IP address, domain name, or port. This is necessary since the frontend will run at `http://localhost:8080`.





But our goal is to process a `.dcm` file so we need to modify our `/backend/src/main.py`. 

Modify it as follows:

```python
from fastapi import FastAPI, UploadFile, HTTPException
from pydicom import dcmread
import numpy as np
from scipy.ndimage import label
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS for your frontend application
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Adjust the origin as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def process_dicom(file: UploadFile, threshold: float = 0.5):
    try:
        # Read DICOM image
        dcm_data = dcmread(file.file)
        pixel_data = dcm_data.pixel_array.astype(float)

        # Normalize pixel data to [0, 1]
        normalized_data = (pixel_data - np.min(pixel_data)) / (np.max(pixel_data) - np.min(pixel_data))

        # Thresholding
        thresholded_data = normalized_data > threshold

        # Calculate volume in mm^3
        voxel_volume = float(dcm_data.SliceThickness) * float(dcm_data.PixelSpacing[0]) * float(dcm_data.PixelSpacing[1])
        labeled_data, num_features = label(thresholded_data)
        volume_mm3 = np.sum(labeled_data) * voxel_volume

        return {
            "success": True,
            "message": "Image processed successfully.",
            "data": {
                "volume_mm3": volume_mm3,
            },
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error processing DICOM: {str(e)}",
            "data": None,
        }

@app.post("/process")
async def process_dcm(file: UploadFile, threshold: float = 0.5):
    result = process_dicom(file, threshold)
    if result["success"]:
        return result["data"]
    else:
        raise HTTPException(status_code=500, detail=result["message"])

```

We basically read a `.dcm` file and its `pixel_array`, and normalizing it and do some arithmetic operation. The point is that the `.dcm` file is being uploaded in frontend and is being processed in backend!


and depends on the content of your backend code you can make request, by typing:

```bash
curl "http://127.0.0.1:5000/process?filename=1-101.dcm&threshold=0.6"
```
or 
```bash
curl -X POST -F "file=@1-101.dcm" -F "threshold=0.6" http://127.0.0.1:5000/process
```
I assume you want that you wan to make a request from backend to make some process on a `.dcm` file with a given `threshold`.






## Vue Setup

To get started with our frontend, we'll scaffold out a project using the Vue CLI.

Make sure you're using version 5.0.8 of the Vue CLI:

```bash
$ vue -V
@vue/cli 5.0.8

# install
$ npm install -g @vue/cli@5.0.8
```
Next, from the "fastapi-vue/services" folder, scaffold out a new Vue project:

```bash
$ vue create frontend
```

Select Default `([Vue 3] babel, eslint)`.

After the scaffold is up, add the [router](https://router.vuejs.org/) (say yes to [history mode](https://router.vuejs.org/guide/essentials/history-mode.html)), and install the required dependencies:


```bash
$ cd frontend
$ vue add router
$ Use history mode for router ? Y
$ npm install --save axios@1.2.1 vuex@4.1.0 bootstrap@5.2.3
```

To serve up the Vue application locally, run:

```bash
$ npm run serve
```

Navigate to `http://localhost:8080/` to view your app.

Kill the server.

Next, wire up the dependencies for Axios and Bootstrap in `services/frontend/src/main.js`:


```javascript
import 'bootstrap/dist/css/bootstrap.css';
import { createApp } from "vue";
import axios from 'axios';

import App from './App.vue';
import router from './router';

const app = createApp(App);

axios.defaults.withCredentials = true;
axios.defaults.baseURL = 'http://localhost:5000/';  // the FastAPI backend

app.use(router);
app.mount("#app");
```

Add a Dockerfile to `services/frontend`:


```dockerfile
FROM node:lts-alpine

WORKDIR /app

ENV PATH /app/node_modules/.bin:$PATH

RUN npm install @vue/cli@5.0.8 -g

COPY package.json .
COPY package-lock.json .
RUN npm install

CMD ["npm", "run", "serve"]

```
Add a `frontend` service to docker-compose.yml:

```dockerfile
version: '3.8'

services:

  backend:
    build: ./services/backend
    ports:
      - 5000:5000
    volumes:
      - backend-data:/app/results  # Define a named volume 'backend-data' and mount it to /app/results in the container
      - ./local_results:/app/results  # Map a local directory 'local_results' to /app/results in the container
    command: uvicorn src.main:app --reload --host 0.0.0.0 --port 5000

  frontend:
    build: ./services/frontend
    volumes:
      - './services/frontend:/app'
      - '/app/node_modules'
    ports:
      - 8080:8080

volumes:
  backend-data:  # Define the named volume 'backend-data'
```

Build the new image and spin up the containers:

```bash
$ docker-compose up -d --build
```

Ensure `http://localhost:8080/` still works.

Next, update `/services/frontend/App.vue` like so:

```vue
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
```

If you did not use docker image and did everything in conda, then you can navigate to the frontend directroy and type the following on the
terminal to initializ the `vue` on the `http://localhost:8080/`: 
```
$npm run serve
```

If you did eveything as I mentioned above, if you brows to `http://localhost:8080/`, then you should see a webpage `DICOM Image Processor
` with two buttons one for `choose file` and the other for `process image`, you can also change the `threshold`.


### Code Explanation of App.vue
#### HTML Template

- The template defines the structure of the component, including the title, file input, threshold input, processing button, and various conditional messages and image displays.

#### JavaScript (Vue.js) Code
- The script section imports the necessary Axios library for making HTTP requests and exports a Vue component.

- The data function initializes the component's data properties, including the selected DICOM file, processing results, error messages, processing status, and the threshold value with a default of 0.5.

- Several methods are defined:
  - uploadDicomFile: This method is triggered when a DICOM file is selected through the file input. It updates the dicomFile property with the selected file.
  - processImages: This method is called when the `Process Images` button is clicked. It performs several tasks:
    - Checks if a DICOM file has been selected and displays an error if not.
    - If a file is selected, it clears any previous error messages and sets the processing status to true.
    - It creates a FormData object and appends the selected DICOM file and the threshold value.
    - It sends a POST request to a specified endpoint (http://localhost:5000/process) with the FormData containing the file and threshold as query parameter.
    - Upon a successful response, it displays the calculated volume in the result section.
    - In case of an error during processing, it displays an error message.
    - Regardless of success or failure, it sets the processing status back to false after completion.



#### Styling
The `<style>` section is left empty for you to add your custom CSS styles to match your application's design.

[Axios](https://axios-http.com/), which is an HTTP client, is used to send AJAX requests to the backend. 

Your full project structure should now look like this:

```
├── docker-compose.yml
└── services
    ├── backend
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   └── src
    │       └── main.py
    └── frontend
        ├── .gitignore
        ├── Dockerfile
        ├── README.md
        ├── babel.config.js
        ├── jsconfig.json
        ├── package-lock.json
        ├── package.json
        ├── public
        │   ├── favicon.ico
        │   └── index.html
        ├── src
        │   ├── App.vue
        │   ├── assets
        │   │   └── logo.png
        │   ├── components
        │   │   └── HelloWorld.vue
        │   ├── main.js
        │   ├── router
        │   │   └── index.js
        │   └── views
        │       ├── AboutView.vue
        │       └── HomeView.vue
        └── vue.config.js
```

# Future directions:
- backend: We can develop sophisticated ML/AI algorithms to process images with different techniques. We can define another service in our docker-compose file to support a data base and write the results of image processing into a `PostgreSQL` or `MySQL`.

- frontend: For this section also we may add many graphical aspects. In particular we can simply make request to our backend api to apply AI/ML algorithms on a given image.


