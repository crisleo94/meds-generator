# Herramientas (Suite Web Multifunción)

Aplicación web desarrollada en **Django + HTMX** con tema oscuro estructurada en dos grandes áreas de trabajo y múltiples utilidades de procesamiento efímero en memoria:

### 💊 1. Farmacia
1. **🖨️ Impresión de Tarjetas A4**: Generación de tarjetas para cenefa (3.5 × 1.5 cm) en formato A4 con soporte dinámico para **1 columna** (texto grande o código de barras grande) o **2 columnas** (título + código/código de barras).
2. **📝 Ordenador de Listas (Reemplazo n8n)**: Limpieza y ordenamiento alfabético estricto en español para listas de texto desordenadas (eliminación de viñetas, comillas, guiones y espacios redundantes), con copia al portapapeles y descarga en `.txt`.
3. **📊 Normalizador de Excel**: Consolidación y desaplanado de múltiples columnas dispersas en un Excel estructurado, ordenado y listo para impresión.

### 🖼️ 2. Imágenes
1. **📝 Extraer Texto (OCR)**: Extracción de texto desde imágenes (fotos, capturas, facturas o documentos) mediante **Tesseract OCR** en memoria RAM. Soporta idiomas español e inglés, preprocesamiento de imagen (contraste, binarización blanco/negro) y copia directa al portapapeles o descarga en `.txt`.
2. **🔄 Convertir Imágenes con FFmpeg**: Conversión instantánea a formatos optimizados (**WebP, JPG, PNG, AVIF, ICO, GIF, BMP**) mediante tuberías FFmpeg (`pipe:0` a `pipe:1`) en memoria RAM, con control interactivo de compresión/calidad, escalado proporcional y eliminación de metadatos EXIF.

---

## 🔒 Garantía de Almacenamiento Cero (Zero-Disk / Ephemeral)

* **Cero persistencia:** Ninguna imagen, texto procesado ni archivo convertido se almacena en el disco, contenedor o nube.
* **Procesamiento en RAM:** Tanto Tesseract OCR como las conversiones de FFmpeg operan directamente sobre flujos binarios en memoria (`io.BytesIO` y tuberías `stdin/stdout`).
* **Descarga inmediata:** Los resultados se sirven directamente al navegador como streams de respuesta HTTP con eliminación instantánea.

Gestionado nativamente con **`uv`** y `pyproject.toml`.

---

## 📐 Especificaciones de Impresión

* **Dimensiones de Tarjeta**: **3.5 cm de ancho × 1.5 cm de alto**.
* **Hoja**: Formato **A4** (21.0 cm × 29.7 cm).
* **Distribución**: **90 tarjetas por hoja** (5 columnas × 18 filas).
* **Márgenes de seguridad**:
  * Laterales: `1.75 cm`
  * Superior e inferior: `1.35 cm`
* **Líneas de corte**: Guías sutiles en gris claro (0.4 pt) diseñadas específicamente para corte con tijera o guillotina manual sobre papel bond u opalina.
* **Tipografía inteligente**: Ajuste adaptativo de tamaño de fuente (8.0 pt a 5.5 pt) y cálculo de saltos de línea equilibrados para evitar desbordes y palabras huérfanas.

---

## 💻 Desarrollo Local con `uv`

1. **Instalar / Sincronizar dependencias**:
   ```bash
   uv sync
   ```

2. **Ejecutar migraciones y recolectar estáticos**:
   ```bash
   uv run python manage.py migrate
   uv run python manage.py collectstatic --noinput
   ```

3. **Iniciar el servidor web**:
   ```bash
   uv run python manage.py runserver
   ```
   Abre [http://127.0.0.1:8000/](http://127.0.0.1:8000/) en tu navegador.

---

## 🚀 Despliegue con Docker (Producción / Nube)

Levantar la aplicación en contenedor utilizando `uv` y `Gunicorn`:

```bash
docker compose up --build -d
```

Acceso:
👉 `http://localhost:8000`

---

## 🛠️ Scripts Independientes (Modo Consola con uv)

Los scripts autónomos para generación directa desde la terminal permanecen intactos:

* **Solo texto y números en negrita**:
  ```bash
  uv run python generar_tarjetas.py
  ```
  Genera: `tarjetas_medicamentos.pdf`

* **Con código de barras Code 128 + número**:
  ```bash
  uv run python generar_tarjetas_con_codigo_barras.py
  ```
  Genera: `tarjetas_medicamentos_con_codigo_barras.pdf`

---

## 🔒 Almacenamiento Efímero

* Los archivos `.xlsx` subidos se procesan en memoria o rutas temporales.
* Al generar y descargar el PDF, el archivo cargado se elimina de forma inmediata y automática para garantizar privacidad y optimización del almacenamiento.
* Tarea periódica de limpieza para purgar cualquier archivo temporal residual mayor a 30 minutos.
