/*
      PASO 1:
      Ajusta la URL base de tu backend (en Heroku).
      Si tu dominio es "https://secret-reef-62358-cf2dfd0a2b98.herokuapp.com",
      ponlo aquí:
    */
const BASE_URL = window.location.origin.includes("localhost")
  ? "http://127.0.0.1:5000"
  : window.location.origin;

/*
      PASO 2:
      Variables globales para manejar el test:
        - testId: para identificar esta sesión de test (puede llegarte desde el servidor o lo generas al inicio).
        - usuario: el nombre o identificador del usuario.
        - preguntaActual: objeto con {id, Pregunta}, que muestra la pregunta en pantalla.
    */
let testId = "Test_12345";
let usuario = "Gorka"; // Podrías pedirlo con un prompt o un formulario
let preguntaActual = null;

// Referencias a elementos del DOM
const textoPregunta = document.getElementById("texto-pregunta");
const respuestaInput = document.getElementById("respuesta-input");
const btnEnviar = document.getElementById("btn-enviar");
const preguntaContainer = document.getElementById("pregunta-container");
const resultadoContainer = document.getElementById("resultado-container");
const textoResultado = document.getElementById("texto-resultado");

// Al cargar la página, iniciamos el test pidiendo la primera pregunta
window.addEventListener("DOMContentLoaded", () => {
  console.log("Page is fully loaded. Running iniciarTest...");
  iniciarTest();
});

/*
      PASO 3:
      Función para iniciar el test. (Podría crear un "usuario" en tu backend,
      o simplemente pedir la primera pregunta adaptativa).
    */

async function iniciarTest() {
  // Ejemplo: Podrías registrar el usuario si lo deseas:
  // await registrarUsuario("Gorka", "gorka@example.com");

  // Llamamos a un endpoint "especial" o "responder" con un "pregunta_actual = null" para que
  // el servidor nos dé la primera pregunta adaptada.
  // En tu caso, hay que modificar /responder en Flask para aceptar esta lógica,
  // o crear un nuevo endpoint (p.e. /siguiente_pregunta).
  try {
    const resp = await fetch(`${BASE_URL}/responder`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        usuario: usuario,
        testId: testId,
        id_pregunta: null,
        respuesta: null,
        peso: 0,
        subtipo_actual: "",
        // mas info si necesitas
      }),
    });
    const data = await resp.json();
    console.log(data.siguiente_pregunta);

    if (data.status === "success") {
      // Asumimos que el servidor nos manda "siguiente_pregunta" y "test_id"
      // Ejemplo:
      // {
      //   "status": "success",
      //   "siguiente_pregunta": { "id": 1, "Pregunta": "¿Te consideras sociable?" },
      //   "test_id": "Test_12345",
      //   "test_finalizado": false
      // }

      // testId = data.test_id || `Test_${Date.now()}`;

      if (data.test_finalizado) {
        // Si por alguna razón ya está finalizado, mostramos resultados
        mostrarResultados(data);
      } else {
        mostrarPregunta(data.siguiente_pregunta);
      }
    } else {
      textoPregunta.textContent = "Error al iniciar test: " + data.message;
      console.error(data);
    }
  } catch (err) {
    textoPregunta.textContent = "Error de conexión al iniciar test.";
    console.error(err);
  }
}

// async function iniciarTest() {
//     try {
//       const resp = await fetch(`${BASE_URL}/iniciar_test`, {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ usuario: usuario, testId: testId }), // Send only required data
//       });

//       const data = await resp.json();
//       console.log(JSON.stringify(data));

//       if (resp.ok) {
//         console.log("Siguiente pregunta:", data.siguiente_pregunta);

//         if (data.test_finalizado) {
//           mostrarResultados(data);
//         } else {
//           mostrarPregunta(data.siguiente_pregunta);
//         }
//       } else {
//         console.error("Error en la respuesta del servidor:", data);
//         textoPregunta.textContent =
//           "Error al iniciar el test: " +
//           (data.message || "Respuesta inválida");
//       }
//     } catch (err) {
//       console.error("Error de conexión:", err);
//       textoPregunta.textContent = "Error de conexión al iniciar test.";
//     }
//   }

/*
      PASO 4:
      Función para mostrar la pregunta recibida del servidor.
    */
function mostrarPregunta(preguntaObj) {
  if (!preguntaObj) {
    // Si no hay siguiente_pregunta, podría ser que el test finalizó
    return;
  }
  preguntaActual = preguntaObj; // {id, Pregunta, ...}
  textoPregunta.textContent = preguntaObj.Pregunta || "Pregunta desconocida";

  // Limpia el valor anterior
  respuestaInput.value = "";
  respuestaInput.focus();

  // Habilitar el botón "Enviar"
  btnEnviar.disabled = false;
}

/*
      PASO 5:
      Manejamos el evento de click en el botón "Enviar".
      Esto envía la respuesta al servidor y espera la siguiente pregunta.
    */
btnEnviar.addEventListener("click", async (event) => {
  event.preventDefault();

  // Validar la respuesta
  const valor = respuestaInput.value;
  if (!valor || valor < 1 || valor > 5) {
    alert("Por favor, ingresa un número entre 1 y 5");
    return;
  }

  // Deshabilitar el botón mientras procesamos
  btnEnviar.disabled = true;

  // Llamar de nuevo a /responder (o /siguiente_pregunta) con la respuesta
  try {
    const resp = await fetch(`${BASE_URL}/responder`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        usuario: usuario,
        id_pregunta: preguntaActual.id, // la pregunta que estamos respondiendo
        respuesta: valor,
        peso: 1, // p.e. 1, o podrías calcular algo
        subtipo_actual: "", // p.e. si lo manejas
        testId: testId,
      }),
    });
    const data = await resp.json();

    if (data.status === "success") {
      /*
            Asumimos que el servidor ahora te devuelve algo como:
            {
              "status": "success",
              "message": "Respuesta registrada",
              "siguiente_pregunta": { "id":7, "Pregunta": "..." },
              "test_finalizado": false,
              "test_id": "Test_12345"
            }
            Si test_finalizado = true, también podría devolverte el ranking y resultado final.
          */
      if (data.test_finalizado) {
        mostrarResultados(data);
      } else {
        // Hay otra pregunta
        mostrarPregunta(data.siguiente_pregunta);
      }
    } else {
      alert("Error: " + data.message);
      console.error(data);
    }
  } catch (err) {
    alert("Error de conexión al enviar respuesta");
    console.error(err);
  }
});

/*
      PASO 6 (opcional):
      Ejemplo de función para registrar un usuario (llama a /registrar_usuario).
      No es obligatorio, pero lo incluyo para que veas cómo podrías hacerlo.
    */
async function registrarUsuario(nombre, correo) {
  try {
    const resp = await fetch(`${BASE_URL}/registrar_usuario`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre, correo }),
    });
    const data = await resp.json();
    if (data.status === "success") {
      console.log("Usuario registrado:", data.message);
    } else {
      console.error("Error al registrar usuario:", data);
    }
  } catch (err) {
    console.error("Error registrando usuario:", err);
  }
}

/*
      PASO 7:
      Función para mostrar resultados y dibujar la gráfica final con Chart.js.
      El servidor, en el 'data', podría enviarte:
        - "ranking": [ ["SubtipoA", 3.2], ["SubtipoB", 2.5], ... ]
        - "resultado": "SubtipoA"
        - "descripcion", "virtudes", etc.
    */
function mostrarResultados(data) {
  // Oculta el contenedor de preguntas
  preguntaContainer.classList.add("oculto");

  // Muestra el contenedor de resultados
  resultadoContainer.classList.remove("oculto");

  // Ejemplo: muestra el subtipo principal
  if (data.resultado) {
    textoResultado.textContent = `Tu subtipo principal es: ${data.resultado}`;
  } else {
    textoResultado.textContent = "Resultado no disponible.";
  }

  // Si trae un ranking, dibujamos el gráfico
  if (data.ranking) {
    dibujarGrafico(data.ranking);
  }
}

/*
      PASO 8:
      Dibujar un gráfico de barras con Chart.js
      data.ranking es un array de arrays, ej: [ ["SubtipoA", 3.2], ["SubtipoB", 2.5], ...]
    */
function dibujarGrafico(ranking) {
  const ctx = document.getElementById("myChart").getContext("2d");
  const labels = ranking.map((item) => item[0]);
  const valores = ranking.map((item) => item[1]);

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Puntuación por Subtipo",
          data: valores,
          backgroundColor: "rgba(75, 192, 192, 0.5)",
          borderColor: "rgba(75, 192, 192, 1)",
          borderWidth: 1,
        },
      ],
    },
    options: {
      scales: {
        y: { beginAtZero: true },
      },
    },
  });
}
