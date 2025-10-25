OCT Disease Classification with Explainable AI and Generative Report Generation

Problem Statement

Retinal diseases such as Choroidal Neovascularization (CNV), Diabetic Macular Edema (DME), and Drusen are major causes of vision impairment and blindness worldwide.
Diagnosing these diseases typically relies on manual interpretation of Optical Coherence Tomography (OCT) scans by expert ophthalmologists — a process that is:

⏱️ Time-consuming and depends on specialist availability

🧍‍♂️ Human-error prone, especially in early-stage disease detection

🌍 Limited in reach, particularly in rural or low-resource regions

❌ Lacking explainability, making AI-based systems hard to trust

Hence, there is a critical need for an automated, interpretable, and accessible system that can analyze OCT scans, classify diseases accurately, and generate understandable medical reports for both doctors and patients.

🎯 Objective

To build an AI-powered diagnostic assistant that:
Automatically classifies OCT retinal images into categories such as Normal, CNV, DME, and Drusen.

Generates human-readable medical summaries using Generative AI (MMR) based on model predictions.

Provides visual explainability (Grad-CAM heatmaps) highlighting diseased regions.

Enables tele-ophthalmology, allowing remote screening and doctor validation.


💡 Proposed Solution
We propose a hybrid AI pipeline combining Medical Imaging Deep Learning (via MONAI) and Generative AI (via MMR — Medical-Model Report Generator) to assist doctors in early retinal disease detection.

🔹 Key Features

🧬 Deep learning model trained on OCT datasets for disease classification

💬 Generative AI module that converts AI predictions into interpretable text reports

☁️ Web portal interface for image upload, instant diagnosis, and report generation

🧑‍⚕️ Doctor dashboard for remote validation and record management

<img width="1024" height="1024" alt="Gemini_Generated_Image_9e55kl9e55kl9e55" src="https://github.com/user-attachments/assets/eb53af61-a430-4cb4-ae44-806f8ae265e0" />


