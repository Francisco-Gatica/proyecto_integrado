import datetime
from io import StringIO
from unittest.mock import MagicMock, patch

import requests
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import CitaMedica, Paciente
from .services import (
    enviar_mensaje_texto,
    enviar_recordatorio_whatsapp,
    mensaje_prueba,
    normalizar_telefono,
)
from .validators import formatear_telefono_cl, parsear_fecha, validar_rut


def _mock_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 300
    resp.json.return_value = json_data if json_data is not None else {}
    resp.text = str(json_data)
    return resp


@override_settings(
    WHATSAPP_TOKEN="test-token-123",
    WHATSAPP_PHONE_ID="1483338058192542",
    WHATSAPP_API_VERSION="v21.0",
    WHATSAPP_TEST_TEMPLATE="hello_world",
    WHATSAPP_TEST_LANGUAGE="en_US",
    WHATSAPP_REMINDER_TEMPLATE="",
)
class WhatsAppServiceTests(TestCase):
    def test_normalizar_telefono(self):
        self.assertEqual(normalizar_telefono("+56 9 1234-5678"), "56912345678")
        with self.assertRaises(ValueError):
            normalizar_telefono("")
        with self.assertRaises(ValueError):
            normalizar_telefono("1234")

    @patch("clinica_dental.services.requests.post")
    def test_mensaje_prueba_plantilla_exitoso(self, mock_post):
        mock_post.return_value = _mock_response(
            200,
            {
                "messaging_product": "whatsapp",
                "contacts": [{"input": "56912345678", "wa_id": "56912345678"}],
                "messages": [{"id": "wamid.HBgNNTY5MTIzNDU2NzgV"}],
            },
        )

        resultado = mensaje_prueba("+56 9 1234 5678")

        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["status_code"], 200)
        self.assertEqual(resultado["message_id"], "wamid.HBgNNTY5MTIzNDU2NzgV")

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://graph.facebook.com/v21.0/1483338058192542/messages")
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-token-123")
        self.assertEqual(kwargs["json"]["type"], "template")
        self.assertEqual(kwargs["json"]["template"]["name"], "hello_world")
        self.assertEqual(kwargs["json"]["to"], "56912345678")

    @patch("clinica_dental.services.requests.post")
    def test_mensaje_prueba_texto_personalizado(self, mock_post):
        mock_post.return_value = _mock_response(
            200,
            {"messages": [{"id": "wamid.TEXTO123"}]},
        )

        resultado = mensaje_prueba(
            "56912345678",
            nombre_paciente="Ana Pérez",
            modo="texto",
            mensaje="Hola Ana, prueba exitosa.",
        )

        self.assertTrue(resultado["ok"])
        self.assertEqual(resultado["message_id"], "wamid.TEXTO123")
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["type"], "text")
        self.assertEqual(payload["text"]["body"], "Hola Ana, prueba exitosa.")

    @patch("clinica_dental.services.requests.post")
    def test_error_meta_api_devuelve_detalle(self, mock_post):
        mock_post.return_value = _mock_response(
            401,
            {"error": {"message": "Invalid OAuth access token.", "code": 190}},
        )

        resultado = enviar_mensaje_texto("56912345678", "Hola")

        self.assertFalse(resultado["ok"])
        self.assertEqual(resultado["status_code"], 401)
        self.assertIn("190", resultado["error"])
        self.assertIn("Invalid OAuth access token.", resultado["error"])

    @patch("clinica_dental.services.requests.post")
    def test_error_red_no_lanza_excepcion(self, mock_post):
        mock_post.side_effect = requests.Timeout("Tiempo de espera agotado")

        resultado = mensaje_prueba("56912345678")

        self.assertFalse(resultado["ok"])
        self.assertIn("Tiempo de espera agotado", resultado["error"])

    @override_settings(WHATSAPP_TOKEN="", WHATSAPP_PHONE_ID="")
    def test_credenciales_faltantes(self):
        resultado = mensaje_prueba("56912345678")
        self.assertFalse(resultado["ok"])
        self.assertIn("WHATSAPP_TOKEN", resultado["error"])

    @override_settings(WHATSAPP_REMINDER_TEMPLATE="recordatorio_cita", WHATSAPP_REMINDER_LANGUAGE="es")
    @patch("clinica_dental.services.requests.post")
    def test_recordatorio_con_plantilla_configurada(self, mock_post):
        mock_post.return_value = _mock_response(200, {"messages": [{"id": "wamid.REC1"}]})

        resultado = enviar_recordatorio_whatsapp(
            "56912345678",
            "Carlos Soto",
            datetime.date(2026, 11, 30),
            datetime.time(10, 30),
        )

        self.assertTrue(resultado["ok"])
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["template"]["name"], "recordatorio_cita")
        params = payload["template"]["components"][0]["parameters"]
        self.assertEqual([p["text"] for p in params], ["Carlos Soto", "30/11/2026", "10:30"])


@override_settings(
    WHATSAPP_TOKEN="test-token-123",
    WHATSAPP_PHONE_ID="1483338058192542",
)
class WhatsAppViewAndSignalTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="asistente", password="password123")

    @patch("clinica_dental.services.requests.post")
    def test_vista_whatsapp_prueba_envia_y_muestra_mensaje(self, mock_post):
        mock_post.return_value = _mock_response(200, {"messages": [{"id": "wamid.WEB1"}]})
        self.client.login(username="asistente", password="password123")

        resp_index = self.client.get(reverse("index"))
        self.assertContains(resp_index, "Probar WhatsApp")

        response = self.client.post(
            reverse("whatsapp_prueba"),
            {"telefono": "+56 9 1234 5678", "modo": "plantilla"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        mensajes = [m.message for m in response.context["messages"]]
        self.assertTrue(any("wamid.WEB1" in msg for msg in mensajes))

    @patch("clinica_dental.services.requests.post")
    def test_crear_cita_paciente_existente_envia_whatsapp(self, mock_post):
        mock_post.return_value = _mock_response(200, {"messages": [{"id": "wamid.CITA1"}]})
        paciente = Paciente.objects.create(
            id_paciente=10,
            nombre="Juan",
            primer_apellido="Pérez",
            telefono="+56 9 1111 2222",
            activo=True,
        )
        self.client.login(username="asistente", password="password123")

        response = self.client.post(
            reverse("cita_crear"),
            {
                "fecha": "05/12/2026",
                "hora_inicio": "10:00",
                "hora_fin": "11:00",
                "estado": "Pendiente",
                "tipo_paciente": "existente",
                "id_paciente": paciente.id_paciente,
                "motivo_consulta": "Control",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["to"], "56911112222")
        self.assertIn("Juan", payload["text"]["body"])
        self.assertIn("05/12/2026", payload["text"]["body"])
        mensajes = [m.message for m in response.context["messages"]]
        self.assertTrue(any("Mensaje de WhatsApp enviado" in msg for msg in mensajes))

    @patch("clinica_dental.services.requests.post")
    def test_crear_cita_paciente_nuevo_envia_whatsapp(self, mock_post):
        mock_post.return_value = _mock_response(200, {"messages": [{"id": "wamid.CITA2"}]})
        self.client.login(username="asistente", password="password123")

        response = self.client.post(
            reverse("cita_crear"),
            {
                "fecha": "06/12/2026",
                "hora_inicio": "15:00",
                "hora_fin": "16:00",
                "estado": "Pendiente",
                "tipo_paciente": "nuevo",
                "nombre_paciente": "Lucía",
                "primer_apellido_paciente": "Gómez",
                "rut_paciente": "11111111-1",
                "fecha_nacimiento_paciente": "15/03/1995",
                "telefono_paciente": "+56933334444",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        paciente = Paciente.objects.get(rut="11111111-1")
        self.assertEqual(paciente.telefono, "+56 9 3333 4444")
        self.assertEqual(paciente.fecha_nacimiento, datetime.date(1995, 3, 15))
        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["to"], "56933334444")
        self.assertIn("Lucía", payload["text"]["body"])

    @patch("clinica_dental.services.requests.post")
    def test_crear_cita_fallo_whatsapp_no_impide_guardar(self, mock_post):
        mock_post.return_value = _mock_response(
            400,
            {"error": {"message": "Recipient phone number not in allowed list", "code": 131030}},
        )
        paciente = Paciente.objects.create(
            id_paciente=11,
            nombre="Pedro",
            primer_apellido="Rojas",
            telefono="+56955556666",
            activo=True,
        )
        self.client.login(username="asistente", password="password123")

        response = self.client.post(
            reverse("cita_crear"),
            {
                "fecha": "07/12/2026",
                "hora_inicio": "11:00",
                "estado": "Pendiente",
                "tipo_paciente": "existente",
                "id_paciente": paciente.id_paciente,
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(CitaMedica.objects.count(), 1)
        mensajes = [m.message for m in response.context["messages"]]
        self.assertTrue(any("No se pudo enviar el WhatsApp" in msg for msg in mensajes))

    def test_crear_cita_rechaza_rut_y_telefono_invalidos(self):
        self.client.login(username="asistente", password="password123")
        response = self.client.post(
            reverse("cita_crear"),
            {
                "fecha": "07/12/2026",
                "hora_inicio": "11:00",
                "tipo_paciente": "nuevo",
                "nombre_paciente": "Ana",
                "primer_apellido_paciente": "Díaz",
                "rut_paciente": "11.111.111-1",
                "telefono_paciente": "+56 9 1111 1111",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(CitaMedica.objects.count(), 0)
        mensajes = [m.message for m in response.context["messages"]]
        self.assertTrue(any("11111111-1" in msg for msg in mensajes))


class ValidacionesFormatoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="asistente_val", password="password123")

    def test_parsear_fecha_ddmmyyyy(self):
        self.assertEqual(parsear_fecha("25/11/2026"), datetime.date(2026, 11, 25))
        with self.assertRaises(ValueError):
            parsear_fecha("31/02/2026")
        with self.assertRaises(ValueError):
            parsear_fecha("25-11-2026")

    def test_validar_rut_formato_11111111_1(self):
        self.assertEqual(validar_rut("11111111-1"), "11111111-1")
        self.assertEqual(validar_rut("9876543-k"), "9876543-K")
        for invalido in ("11.111.111-1", "111111111", "111111-1", "11111111-A"):
            with self.assertRaises(ValueError):
                validar_rut(invalido)

    def test_formatear_telefono_cl(self):
        self.assertEqual(formatear_telefono_cl("+56911111111"), "+56 9 1111 1111")
        self.assertEqual(formatear_telefono_cl("56911111111"), "+56 9 1111 1111")
        self.assertEqual(formatear_telefono_cl("911111111"), "+56 9 1111 1111")
        self.assertEqual(formatear_telefono_cl("+56 9 1111 1111"), "+56 9 1111 1111")
        for invalido in ("1234", "+56 8 1111 1111", "+1 555 179 6543"):
            with self.assertRaises(ValueError):
                formatear_telefono_cl(invalido)

    def test_paciente_crear_y_editar_validan_y_formatean(self):
        self.client.login(username="asistente_val", password="password123")

        resp_bad = self.client.post(
            reverse("paciente_crear"),
            {
                "nombre": "Sofía",
                "primer_apellido": "Mora",
                "rut": "111111111",
                "telefono": "+56922223333",
                "fecha_nacimiento": "01/05/1990",
            },
            follow=True,
        )
        self.assertEqual(Paciente.objects.count(), 0)
        self.assertTrue(any("11111111-1" in m.message for m in resp_bad.context["messages"]))

        resp_ok = self.client.post(
            reverse("paciente_crear"),
            {
                "nombre": "Sofía",
                "primer_apellido": "Mora",
                "rut": "11111111-k",
                "telefono": "922223333",
                "fecha_nacimiento": "01/05/1990",
            },
            follow=True,
        )
        self.assertEqual(resp_ok.status_code, 200)
        pac = Paciente.objects.get(rut="11111111-K")
        self.assertEqual(pac.telefono, "+56 9 2222 3333")
        self.assertEqual(pac.fecha_nacimiento, datetime.date(1990, 5, 1))

        resp_list = self.client.get(reverse("pacientes"))
        self.assertContains(resp_list, "+56 9 2222 3333")
        self.assertContains(resp_list, "01/05/1990")

    @patch("clinica_dental.services.requests.post")
    def test_signal_confirmacion_cita_envia_recordatorio(self, mock_post):
        mock_post.return_value = _mock_response(200, {"messages": [{"id": "wamid.SIG1"}]})
        cita = CitaMedica.objects.create(
            id_cita=1,
            fecha=datetime.date(2026, 12, 1),
            hora_inicio=datetime.time(9, 0),
            hora_fin=datetime.time(10, 0),
            estado="Pendiente",
        )
        Paciente.objects.create(
            id_paciente=1,
            nombre="María",
            primer_apellido="López",
            telefono="+56 9 8765 4321",
            id_cita=cita,
            activo=True,
        )

        cita.estado = "Confirmada"
        cita.save()

        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["to"], "56987654321")
        self.assertIn("María", payload["text"]["body"])

    def test_management_command_probar_whatsapp_dry_run(self):
        out = StringIO()
        call_command("probar_whatsapp", "+56912345678", "--modo", "texto", "--dry-run", stdout=out)
        salida = out.getvalue()
        self.assertIn('"ok": true', salida)
        self.assertIn("56912345678", salida)

    def test_management_command_telefono_invalido(self):
        out = StringIO()
        with self.assertRaises(CommandError):
            call_command("probar_whatsapp", "123", "--dry-run", stdout=out)
