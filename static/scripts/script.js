// Variable global para almacenar el ID de la cita en edición
let citaIdActual = null;

/**
 * Abre el modal para agendar una nueva cita médica.
 * @param {string}
 * @param {string}
 * @param {string}
 */

function abrirModalNuevaCita(fecha, horaInicio, horaFin) {
    const inputFecha = document.getElementById('nuevaFecha');
    const inputHoraInicio = document.getElementById('nuevaHoraInicio');
    const inputHoraFin = document.getElementById('nuevaHoraFin');

    if (inputFecha) inputFecha.value = fecha || '';
    if (inputHoraInicio) inputHoraInicio.value = horaInicio || '09:00';
    if (inputHoraFin) inputHoraFin.value = horaFin || '10:00';

    // Reiniciar selector de tipo de paciente a "existente"
    const radioExistente = document.getElementById('tipoExistente');
    if (radioExistente) {
        radioExistente.checked = true;
        toggleFormPaciente('existente');
    }

    const modalElement = document.getElementById('modalNuevaCita');
    if (modalElement) {
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        modal.show();
    }
}
/**
 * Alterna entre la selección de un paciente existente o el registro de uno nuevo.
 * @param {string} tipo - 'existente' o 'nuevo'
 */
function toggleFormPaciente(tipo) {
    const seccionExistente = document.getElementById('seccionPacienteExistente');
    const seccionNuevo = document.getElementById('seccionPacienteNuevo');

    if (!seccionExistente || !seccionNuevo) return;

    if (tipo === 'nuevo') {
        seccionExistente.style.display = 'none';
        seccionNuevo.style.display = 'block';
    } else {
        seccionExistente.style.display = 'block';
        seccionNuevo.style.display = 'none';
    }
}
/**
 * Abre el modal con el detalle de la cita para visualizarla o modificarla.
 * @param {number|string} idCita - ID de la cita
 * @param {string} fecha - Fecha en formato DD/MM/YYYY
 * @param {string} horaInicio - Hora de inicio en formato HH:MM
 * @param {string} horaFin - Hora de término en formato HH:MM
 * @param {number|string} doctorId - ID del doctor asignado
 * @param {number|string} pacienteId - ID del paciente asignado
 * @param {string} pacienteNombre - Nombre completo del paciente
 * @param {string} estado - Estado de la cita (Pendiente, Confirmada, Realizada, Cancelada)
 * @param {string} motivo - Motivo o descripción de la consulta
 */
function abrirModalDetalleCita(idCita, fecha, horaInicio, horaFin, doctorId, pacienteId, pacienteNombre, estado, motivo) {
    citaIdActual = idCita;
    
    const formEditar = document.getElementById('formEditarCita');
    const formEliminar = document.getElementById('formEliminarCitaOculto');

    // Construcción de rutas dinámicas para edición y eliminación
    if (formEditar) formEditar.action = `/citas/${idCita}/editar/`;
    if (formEliminar) formEliminar.action = `/citas/${idCita}/eliminar/`;

    const detalleNombre = document.getElementById('detalleNombrePaciente');
    if (detalleNombre) {
        detalleNombre.innerText = pacienteNombre || '(Sin paciente)';
    }

    const badge = document.getElementById('detalleBadgeEstado');
    if (badge) {
        badge.innerText = estado || 'Pendiente';
        badge.className = 'badge p-2 px-3 rounded-pill fs-6';
        if (estado === 'Confirmada') {
            badge.classList.add('bg-success');
        } else if (estado === 'Pendiente') {
            badge.classList.add('bg-warning', 'text-dark');
        } else if (estado === 'Realizada') {
            badge.classList.add('bg-primary');
        } else if (estado === 'Cancelada') {
            badge.classList.add('bg-danger');
        } else {
            badge.classList.add('bg-secondary');
        }
    }

    // Cargar datos en los campos del formulario
    const inputFecha = document.getElementById('editarFecha');
    const inputHoraInicio = document.getElementById('editarHoraInicio');
    const inputHoraFin = document.getElementById('editarHoraFin');
    const selectDoctor = document.getElementById('editarDoctor');
    const selectPaciente = document.getElementById('editarPaciente');
    const selectEstado = document.getElementById('editarEstado');
    const textareaMotivo = document.getElementById('editarMotivo');

    if (inputFecha) inputFecha.value = fecha || '';
    if (inputHoraInicio) inputHoraInicio.value = horaInicio || '';
    if (inputHoraFin) inputHoraFin.value = horaFin || '';
    if (selectDoctor) selectDoctor.value = doctorId || '';
    if (selectPaciente) selectPaciente.value = pacienteId || '';
    if (selectEstado) selectEstado.value = estado || 'Pendiente';
    if (textareaMotivo) textareaMotivo.value = motivo || '';

    const modalElement = document.getElementById('modalDetalleCita');
    if (modalElement) {
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        modal.show();
    }
}

function solicitarEliminarCita() {
    if (confirm('¿Está seguro de que desea eliminar esta hora de atención? Esta acción no se puede deshacer.')) {
        const formEliminar = document.getElementById('formEliminarCitaOculto');
        if (formEliminar) {
            formEliminar.submit();
        }
    }
}

function filtrarTablaPacientes() {
    const input = document.getElementById('filtroPacientesInput');
    const table = document.getElementById('tablaPacientesModal');
    if (!input || !table) return;

    const filter = input.value.toLowerCase();
    const tr = table.getElementsByTagName('tr');

    for (let i = 1; i < tr.length; i++) {
        let visible = false;
        const tds = tr[i].getElementsByTagName('td');
        for (let j = 0; j < tds.length; j++) {
            if (tds[j]) {
                if (tds[j].innerText.toLowerCase().indexOf(filter) > -1) {
                    visible = true;
                    break;
                }
            }
        }
        tr[i].style.display = visible ? '' : 'none';
    }
}

/**
 * Abre el modal para modificar los datos de un paciente.
 */
function abrirModalEditarPaciente(idPaciente, rut, nombre, primerApellido, segundoApellido, telefono, correo, activo, fechaNacimiento) {
    const formEditar = document.getElementById('formEditarPaciente');
    if (formEditar) {
        formEditar.action = `/pacientes/${idPaciente}/editar/`;
    }

    const inputNombre = document.getElementById('editarNombrePaciente');
    const inputPrimerApellido = document.getElementById('editarPrimerApellidoPaciente');
    const inputSegundoApellido = document.getElementById('editarSegundoApellidoPaciente');
    const inputRut = document.getElementById('editarRutPaciente');
    const inputTelefono = document.getElementById('editarTelefonoPaciente');
    const inputCorreo = document.getElementById('editarCorreoPaciente');
    const inputFechaNacimiento = document.getElementById('editarFechaNacimientoPaciente');
    const selectActivo = document.getElementById('editarActivoPaciente');

    if (inputNombre) inputNombre.value = nombre || '';
    if (inputPrimerApellido) inputPrimerApellido.value = primerApellido || '';
    if (inputSegundoApellido) inputSegundoApellido.value = segundoApellido || '';
    if (inputRut) inputRut.value = rut || '';
    if (inputTelefono) inputTelefono.value = telefono || '';
    if (inputCorreo) inputCorreo.value = correo || '';
    if (inputFechaNacimiento) inputFechaNacimiento.value = fechaNacimiento || '';
    if (selectActivo) selectActivo.value = (activo === 'true' || activo === true) ? 'true' : 'false';

    const modalElement = document.getElementById('modalEditarPaciente');
    if (modalElement) {
        const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
        modal.show();
    }
}

window.abrirModalNuevaCita = abrirModalNuevaCita;
window.toggleFormPaciente = toggleFormPaciente;
window.abrirModalDetalleCita = abrirModalDetalleCita;
window.solicitarEliminarCita = solicitarEliminarCita;
window.filtrarTablaPacientes = filtrarTablaPacientes;
window.abrirModalEditarPaciente = abrirModalEditarPaciente;

function esFechaValidaDDMMYYYY(valor) {
    const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec((valor || '').trim());
    if (!match) return false;
    const dia = parseInt(match[1], 10);
    const mes = parseInt(match[2], 10);
    const anio = parseInt(match[3], 10);
    const fecha = new Date(anio, mes - 1, dia);
    return (
        fecha.getFullYear() === anio &&
        fecha.getMonth() === mes - 1 &&
        fecha.getDate() === dia
    );
}

function aplicarMascaraFecha(input) {
    const digitos = input.value.replace(/\D/g, '').slice(0, 8);
    let formateado = digitos;
    if (digitos.length > 4) {
        formateado = `${digitos.slice(0, 2)}/${digitos.slice(2, 4)}/${digitos.slice(4)}`;
    } else if (digitos.length > 2) {
        formateado = `${digitos.slice(0, 2)}/${digitos.slice(2)}`;
    }
    input.value = formateado;

    if (formateado.length === 0) {
        input.setCustomValidity('');
    } else if (!esFechaValidaDDMMYYYY(formateado)) {
        input.setCustomValidity('Ingrese una fecha válida en formato DD/MM/YYYY.');
    } else {
        input.setCustomValidity('');
    }
}

function validarInputRut(input) {
    let valor = input.value.replace(/[^0-9kK-]/g, '').toUpperCase();
    // Si hay más de un guión, conservar solo el primero
    const partes = valor.split('-');
    if (partes.length > 2) {
        valor = `${partes[0]}-${partes.slice(1).join('')}`;
    }
    input.value = valor;

    if (!valor) {
        input.setCustomValidity('');
    } else if (!/^\d{7,8}-[0-9K]$/.test(valor)) {
        input.setCustomValidity('El RUT debe tener formato 11111111-1 (sin puntos y con guión).');
    } else {
        input.setCustomValidity('');
    }
}

function formatearYValidarTelefono(input) {
    let digitos = input.value.replace(/\D/g, '');
    if (!digitos) {
        input.value = '';
        input.setCustomValidity('');
        return;
    }

    if (digitos.startsWith('56')) {
        digitos = digitos.slice(2);
    }
    digitos = digitos.slice(0, 9);

    let resultado = '+56';
    if (digitos.length > 0) {
        resultado += ` ${digitos.slice(0, 1)}`;
    }
    if (digitos.length > 1) {
        resultado += ` ${digitos.slice(1, 5)}`;
    }
    if (digitos.length > 5) {
        resultado += ` ${digitos.slice(5, 9)}`;
    }
    input.value = resultado;

    if (!/^\+56 9 \d{4} \d{4}$/.test(resultado)) {
        input.setCustomValidity('El teléfono debe tener formato +56 9 1111 1111.');
    } else {
        input.setCustomValidity('');
    }
}

function irAFecha(valor) {
    if (esFechaValidaDDMMYYYY(valor)) {
        location.href = `?fecha=${encodeURIComponent(valor.trim())}`;
    }
}
window.irAFecha = irAFecha;

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[data-date-mask="true"]').forEach((input) => {
        input.addEventListener('input', () => aplicarMascaraFecha(input));
        input.addEventListener('blur', () => aplicarMascaraFecha(input));
    });

    document.querySelectorAll('[data-rut-input="true"]').forEach((input) => {
        input.addEventListener('input', () => validarInputRut(input));
        input.addEventListener('blur', () => validarInputRut(input));
    });

    document.querySelectorAll('[data-phone-mask="true"]').forEach((input) => {
        input.addEventListener('input', () => formatearYValidarTelefono(input));
        input.addEventListener('blur', () => formatearYValidarTelefono(input));
    });
});
