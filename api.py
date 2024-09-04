from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
import time

app = Flask(__name__)

def get_sunat_data(ruc_number):
    # Inicializar el WebDriver en modo headless
    options = webdriver.ChromeOptions()
    #options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=options)

    info_dict = {
        "Resultado de la Búsqueda": {},
        "Representante_Legal": {},
        "Otros_Representantes": [],
        "Establecimientos_Anexos": []
    }

    try:
        # Abrir la página de SUNAT
        driver.get("https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/jcrS00Alias")
        time.sleep(2)  # Esperar a que la página cargue

        # Ingresar el número de RUC
        ruc_input = driver.find_element(By.ID, "txtRuc")
        ruc_input.send_keys(ruc_number)

        # Hacer clic en el botón de "Buscar"
        buscar_button = driver.find_element(By.ID, "btnAceptar")
        buscar_button.click()
        time.sleep(2)  # Esperar a que se cargue la información

        wait = WebDriverWait(driver, 10)

        # Extraer la información de resultado
        try:
            info_container = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div/div[2]/div/div[3]")))
            info_text = info_container.text

            # Procesar el texto en un diccionario estructurado
            info_lines = info_text.split('\n')
            result_dict = {}
            current_key = None
            result_value = ""

            for line in info_lines:
                line = line.strip()
                if not line:
                    continue
                if ':' in line:
                    if current_key:
                        result_dict[current_key] = result_value.strip()
                    current_key, result_value = map(str.strip, line.split(':', 1))
                else:
                    result_value += '\n' + line
            
            if current_key:
                result_dict[current_key] = result_value.strip()

            info_dict["Resultado de la Búsqueda"] = result_dict

            # Intentar extraer la información del representante legal
            try:
                representante_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Representante(s) Legal(es)')]")))
                driver.execute_script("arguments[0].scrollIntoView();", representante_button)
                representante_button.click()
                time.sleep(2)

                representante_info = {
                    "Documento": wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div/div[2]/div[2]/div[2]/div/div/table/tbody/tr[1]/td[1]"))).text.strip(),
                    "Nro. Documento": wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div/div[2]/div[2]/div[2]/div/div/table/tbody/tr[1]/td[2]"))).text.strip(),
                    "Nombre": wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div/div[2]/div[2]/div[2]/div/div/table/tbody/tr[1]/td[3]"))).text.strip(),
                    "Cargo": wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div/div[2]/div[2]/div[2]/div/div/table/tbody/tr[1]/td[4]"))).text.strip(),
                    "Fecha Desde": wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div/div[2]/div[2]/div[2]/div/div/table/tbody/tr[1]/td[5]"))).text.strip()
                }

                additional_info = []
                rows = driver.find_elements(By.XPATH, "/html/body/div/div[2]/div[2]/div[2]/div/div/table/tbody/tr")[1:]

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

                info_dict["Representante_Legal"] = representante_info
                info_dict["Otros_Representantes"] = additional_info

            except Exception as e:
                info_dict["Representante_Legal"] = "No existe información de representante legal"

            # Volver a la página anterior para consultar los establecimientos anexos
            driver.find_element(By.XPATH, "//button[contains(text(), 'Volver')]").click()
            time.sleep(2)

            try:
                establecimientos_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Establecimiento(s) Anexo(s)')]")))
                driver.execute_script("arguments[0].scrollIntoView();", establecimientos_button)
                establecimientos_button.click()
                time.sleep(2)

                establecimientos_anexos = []
                rows = driver.find_elements(By.XPATH, '//*[@id="print"]/div/table/tbody/tr')
                
                for row in rows:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) >= 4:
                        establecimientos_anexos.append({
                            "Código": cols[0].text.strip(),
                            "Tipo de Establecimiento": cols[1].text.strip(),
                            "Dirección": cols[2].text.strip(),
                            "Actividad Económica": cols[3].text.strip()
                        })

                info_dict["Establecimientos_Anexos"] = establecimientos_anexos

            except Exception as e:
                pass

        except Exception as e:
            print(f"Error al extraer información: {e}")

    finally:
        driver.quit()

    return info_dict


@app.route('/consulta_ruc', methods=['POST'])
def consulta_ruc():
    ruc_number = request.form.get('RUC')
    if not ruc_number:
        return jsonify({"error": "RUC no proporcionado"}), 400

    # Obtener la información de SUNAT usando Selenium
    sunat_data = get_sunat_data(ruc_number)

    return jsonify(sunat_data)


if __name__ == '__main__':
    app.run(debug=True, port=5001)
