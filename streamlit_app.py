import Detector
import cv2 as cv
import numpy as np
import streamlit as st
import pandas as pd
import tempfile
import time
import os

# Color de la caja de la bib
color = [252, 15, 192]

# Crear directorio de detección en vivo
if not os.path.exists('./live_detection'):
        os.makedirs('./live_detection')

# Título de la aplicación y modo
st.title('Detector de Números de Dorsal')
st.sidebar.header("Modo")
mode = st.sidebar.radio(
    'Selecciona el modo',
    options=['Demo', 'Imagen', 'Video', 'En Vivo']
)

if mode == 'Imagen':
    # Obtener imagen del usuario
    user_file = st.file_uploader(label='Imagen para analizar:',
        type=['jpg', 'png'])

    button_loc = st.empty()
    
    # Mostrar imagen y convertirla para predicción
    if user_file is not None:
            text_loc = st.empty()
            text_loc.text('Esta es tu imagen:')
            # Convertir el archivo a una imagen de OpenCV.
            file_bytes = np.asarray(bytearray(user_file.read()), dtype=np.uint8)
            img = cv.imdecode(file_bytes, 1)
            img_loc = st.empty()
            img_loc.image(img, channels='BGR')

            if button_loc.button('Detectar'):
                # Obtener predicción de bib
                output = Detector.get_rbns(img)

                # Anotar imagen
                if output is not None:
                    text_loc.text(f"Detectados {len(output)} número(s) de dorsal")
                    for detection in output:
                        img = Detector.annotate(img, detection, color)
                else:
                    text_loc.text("No se detectaron números de dorsal")

                # Mostrar imagen anotada
                img_loc.image(img, channels='BGR')

elif mode == 'En Vivo':
    run = st.checkbox("Activar cámara")
    cap = cv.VideoCapture(0)  # Índice 0 para la cámara web predeterminada
    frame_loc = st.empty()

    if run:
        while True:
            ret, frame = cap.read()
            if not ret:
                st.text("Error en la captura de la cámara")
                break

            # Realizar la detección en el frame actual
            output = Detector.get_rbns(frame, single=True)

            # Anotar el frame con los resultados de la detección
            if output:
                frame = Detector.annotate(frame, output[0], color)
                st.text(f"Detección exitosa: {output[0][0]}")
                # Guardar captura
                cv.imwrite('live_detection/detection_{}.jpg'.format(output[0][0]), frame)
                # Guardar número en un archivo txt
                with open('live_detection/detection.txt', 'a') as f:
                    f.write(f'{output[0][0]}\n')
            # Mostrar el frame en Streamlit
            frame_loc.image(frame, channels='BGR', use_column_width=True)

            time.sleep(1)  # Pausa para control de flujo
    else:
        cap.release()

else:
    if mode == 'Demo':
        video_path = 'Data/bib_detector_demo.mp4'
        video_file = open(video_path, 'rb')
        video_bytes = video_file.read()

    elif mode == 'Video':
        video_bytes = st.file_uploader(label='Vídeo para análisis:',
        type=['mp4'])
        # Usar archivo temporal para OpenCV con video subido por el usuario
        if video_bytes is None:
            st.stop()
        else:
            tfile = tempfile.NamedTemporaryFile(delete=False)
            tfile.write(video_bytes.read())
            video_path = tfile.name

    button_loc = st.empty()
    text_loc = st.empty()
    video_loc = st.empty()

    video_loc.video(video_bytes)

    if button_loc.button('Detectar'):
        # Abrir video para detección
        cap = cv.VideoCapture(video_path)
        cap.set(cv.CAP_PROP_FPS, 25)
        # Establecer especificaciones de salida
        fourcc = cv.VideoWriter_fourcc('m','p','4','v')
        width = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))
        num_frames = cap.get(cv.CAP_PROP_FRAME_COUNT)
        vid_out = cv.VideoWriter('Data/output.mp4', fourcc, 25.0, (width,height))

        frames_complete = 0
        rank = []
        prev_rbn = None
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            # Obtener predicción de bib
            output = Detector.get_rbns(frame, single=True)

            # Anotar imagen
            if output is not None:
                frame = Detector.annotate(frame, output[0], color)

                if prev_rbn is None or prev_rbn != output[0][0]:
                    rbn_count = 0
                    prev_rbn = output[0][0]
                else:
                    rbn_count += 1
                
                if rbn_count >= 25 and prev_rbn not in rank:
                    rank.append(prev_rbn)

            # Guardar frame anotado
            vid_out.write(frame)
            frames_complete += 1
            video_loc.progress(frames_complete / num_frames)

        cap.release()
        vid_out.release()

        button_loc.text("Completo. Presiona play para ver el vídeo anotado.")
        video_file = open('Data/output.mp4', 'rb')
        video_bytes = video_file.read()
        video_loc.video(video_bytes)

        st.header("Orden de llegada")
        for i, rbn in enumerate(rank):
            st.subheader(f'{i+1}.  {rbn}')