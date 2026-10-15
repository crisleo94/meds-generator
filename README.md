# Generador de Tarjetas de Medicamentos A4 (Cenefas y Etiquetas)

Aplicación web desarrollada en **Django + HTMX** con tema oscuro para la importación de archivos Excel (`.xlsx`), mapeo interactivo de columnas, generación de códigos de barras vectoriales **Code 128** y exportación de tarjetas de medicamentos en formato estándar **A4** listas para impresión y corte manual.

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
