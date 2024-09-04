from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json

# Inicializar el WebDriver de Chrome
driver = webdriver.Chrome()

try:
    # Abrir la página de SUNAT
    driver.get("https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/jcrS00Alias")
    time.sleep(2)  # Esperar a que la página cargue

    # Ingresar el número de RUC
    numero_ruc = "20552103816"  # Reemplaza con el RUC deseado
    ruc_input = driver.find_element(By.ID, "txtRuc")
    ruc_input.send_keys(numero_ruc)

    # Hacer clic en el botón de "Buscar"
    buscar_button = driver.find_element(By.ID, "btnAceptar")
    buscar_button.click()
    time.sleep(2)  # Esperar a que se cargue la información

    # Espera explícita para el contenedor de la información
    wait = WebDriverWait(driver, 10)
    try:
        # Esperar a que la información de resultado esté disponible
        info_container = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div/div[2]/div/div[3]")))

        # Extraer el texto completo dentro del contenedor especificado
        info_text = info_container.text

        # Convertir el texto a un diccionario estructurado
        info_lines = info_text.split('\n')
        result_dict = {}
        current_key = None
        result_value = ""

        for line in info_lines:
            line = line.strip()
            if not line:
                continue
            if ':' in line:
                # Si ya había una clave actual, se añade su valor
                if current_key:
                    result_dict[current_key] = result_value.strip()
                # Se actualiza la clave actual y el valor
                current_key, result_value = map(str.strip, line.split(':', 1))
            else:
                # Se añade la línea al valor actual
                result_value += '\n' + line
        
        # Añadir la última entrada si existe
        if current_key:
            result_dict[current_key] = result_value.strip()

        # Guardar la información en un diccionario final
        info_dict = {
            "Resultado de la Búsqueda": result_dict,
            "Representante_Legal": {},
            "Otros_Representantes": [],
            "Establecimientos_Anexos": []
        }

        try:
            # Intentar encontrar y hacer clic en el botón "Representante(s) Legal(es)"
            representante_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Representante(s) Legal(es)')]")))
            
            # Hacer scroll para asegurar que el botón esté visible (opcional)
            driver.execute_script("arguments[0].scrollIntoView();", representante_button)
            representante_button.click()
            
            # Esperar a que se cargue la información del representante legal
            time.sleep(2)

            # Extraer la información tabulada del representante legal desde los XPaths proporcionados
            representante_info = {
                "Documento": wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div/div[2]/div[2]/div[2]/div/div/table/tbody/tr[1]/td[1]"))).text.strip(),
                "Nro. Documento": wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div/div[2]/div[2]/div[2]/div/div/table/tbody/tr[1]/td[2]"))).text.strip(),
                "Nombre": wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div/div[2]/div[2]/div[2]/div/div/table/tbody/tr[1]/td[3]"))).text.strip(),
                "Cargo": wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div/div[2]/div[2]/div[2]/div/div/table/tbody/tr[1]/td[4]"))).text.strip(),
                "Fecha Desde": wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div/div[2]/div[2]/div[2]/div/div/table/tbody/tr[1]/td[5]"))).text.strip()
            }

            # Extraer más información debajo de la tabla si existe
            additional_info = []
            rows = driver.find_elements(By.XPATH, "/html/body/div/div[2]/div[2]/div[2]/div/div/table/tbody/tr")[1:]  # Excluir la primera fila que ya se extrajo

            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) > 0:
                    additional_info.append({
                        "Documento": cols[0].text.strip(),
                        "Nro. Documento": cols[1].text.strip(),
                        "Nombre": cols[2].text.strip(),
                        "Cargo": cols[3].text.strip(),
                        "Fecha Desde": cols[4].text.strip()
                    })

            # Añadir la información tabulada del representante legal y los datos adicionales al diccionario final
            info_dict["Representante_Legal"] = representante_info
            info_dict["Otros_Representantes"] = additional_info

        except Exception as e:
            print("No se encontró el botón 'Representante(s) Legal(es)' o no se pudo extraer la información: ", e)
            # Agregar un mensaje indicando que no hay información disponible
            info_dict["Representante_Legal"] = "No existe información de representante legal"

        # Volver a la página anterior para consultar los establecimientos anexos
        driver.find_element(By.XPATH, "//button[contains(text(), 'Volver')]").click()
        time.sleep(2)  # Esperar a que se cargue la página

        try:
            # Intentar encontrar y hacer clic en el botón "Establecimiento(s) Anexo(s)"
            establecimientos_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Establecimiento(s) Anexo(s)')]")))
            driver.execute_script("arguments[0].scrollIntoView();", establecimientos_button)
            establecimientos_button.click()
            time.sleep(2)  # Esperar a que se cargue la información de los establecimientos anexos

            # Extraer la información de los establecimientos anexos desde las filas de la tabla
            establecimientos_anexos = []
            rows = driver.find_elements(By.XPATH, '//*[@id="print"]/div/table/tbody/tr')
            
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 4:  # Asegurarse de que hay suficientes columnas
                    establecimientos_anexos.append({
                        "Código": cols[0].text.strip(),
                        "Tipo de Establecimiento": cols[1].text.strip(),
                        "Dirección": cols[2].text.strip(),
                        "Actividad Económica": cols[3].text.strip()
                    })

            # Añadir la información de los establecimientos anexos al diccionario final
            info_dict["Establecimientos_Anexos"] = establecimientos_anexos

        except Exception as e:
            print("No se encontró la sección de 'Establecimientos Anexos' o no se pudo extraer la información: ", e)
            # No hacer nada si no se encuentra la sección de establecimientos anexos

    except Exception as e:
        print(f"Error al extraer información: {e}")

    # Guardar la información en un archivo JSON
    with open('consulta_ruc.json', 'w', encoding='utf-8') as json_file:
        json.dump(info_dict, json_file, ensure_ascii=False, indent=4)

    print("Información guardada exitosamente en consulta_ruc.json")

finally:
    # Cerrar el navegador
    driver.quit()
