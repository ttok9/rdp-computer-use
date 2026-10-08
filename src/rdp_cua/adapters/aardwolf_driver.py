from __future__ import annotations

import asyncio
import io
from urllib.parse import quote

from ..coordinates import denormalize_coordinate
from ..models import Action, ActionKind, Observation


class AardwolfDriver:
    """Minimal aardwolf adapter with lazy imports and no credential logging."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        *,
        domain: str = "",
        port: int = 3389,
        width: int = 1920,
        height: int = 1080,
        auth: str = "ntlm",
    ) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.domain = domain
        self.port = port
        self.width = width
        self.height = height
        if auth not in {"ntlm", "tls"}:
            raise ValueError("auth must be ntlm or tls")
        self.auth = auth
        self.connection = None
        self._video_format = None
        self._mouse_button = None

    def _rdp_url(self) -> str:
        qualified_user = f"{self.domain}\\{self.username}" if self.domain else self.username
        scheme = "rdp+ntlm-password" if self.auth == "ntlm" else "rdp"
        host = f"[{self.host}]" if ":" in self.host and not self.host.startswith("[") else self.host
        return f"{scheme}://{quote(qualified_user, safe='')}:{quote(self.password, safe='')}@{host}:{self.port}"

    async def connect(self) -> None:
        try:
            from aardwolf.commons.factory import RDPConnectionFactory
            from aardwolf.commons.iosettings import RDPIOSettings
            from aardwolf.commons.queuedata.constants import MOUSEBUTTON, VIDEO_FORMAT
            from aardwolf.protocol.x224.constants import SUPP_PROTOCOLS
        except ImportError as exc:
            raise RuntimeError("install the 'rdp' extra: python -m pip install -e '.[rdp]'") from exc

        settings = RDPIOSettings()
        settings.channels = []
        settings.video_width = self.width
        settings.video_height = self.height
        settings.video_bpp_min = 15
        settings.video_bpp_max = 32
        settings.video_out_format = VIDEO_FORMAT.PNG
        settings.clipboard_use_pyperclip = False
        settings.supported_protocols = SUPP_PROTOCOLS.HYBRID if self.auth == "ntlm" else SUPP_PROTOCOLS.SSL

        factory = RDPConnectionFactory.from_url(self._rdp_url(), settings)
        self.connection = factory.create_connection_newtarget(self.host, settings)
        try:
            _, error = await self.connection.connect()
            if error is not None:
                raise RuntimeError("RDP connection failed") from error
        except BaseException:
            try:
                await self.disconnect()
            except Exception:
                pass
            raise
        self._video_format = VIDEO_FORMAT
        self._mouse_button = MOUSEBUTTON
        await asyncio.sleep(1)

    async def disconnect(self) -> None:
        connection, self.connection = self.connection, None
        if connection is not None:
            await asyncio.wait_for(connection.terminate(), timeout=5)

    async def capture(self) -> Observation:
        if self.connection is None or self._video_format is None:
            raise RuntimeError("RDP driver is not connected")
        if not getattr(self.connection, "desktop_buffer_has_data", False):
            raise RuntimeError("RDP desktop frame is not available")
        image = self.connection.get_desktop_buffer(self._video_format.PIL)
        if image is None:
            raise RuntimeError("RDP desktop buffer is empty")
        output = io.BytesIO()
        image.save(output, "PNG")
        self.width, self.height = image.size
        return Observation(output.getvalue(), self.width, self.height)

    async def execute(self, action: Action) -> None:
        if self.connection is None:
            raise RuntimeError("RDP driver is not connected")
        if action.kind is ActionKind.WAIT:
            await asyncio.sleep(action.seconds or 0)
            return
        if action.kind is ActionKind.TYPE:
            await self._type_text(action.text or "")
            return
        if action.kind is ActionKind.KEY:
            await self._press_key(action.key or "")
            return
        if action.kind is ActionKind.SCROLL:
            if self._mouse_button is None:
                raise RuntimeError("RDP mouse constants are not initialized")
            x, y = denormalize_coordinate(action.coordinate or (500, 500), self.width, self.height)
            # In aardwolf 0.2.13 the UP path sets WHEEL. A signed rotation encodes
            # the direction, avoiding its DOWN path (which omits the WHEEL bit).
            button = self._mouse_button.MOUSEBUTTON_WHEEL_UP
            rotation = 120 if (action.scroll_delta or 0) > 0 else -120
            for _ in range(abs(action.scroll_delta or 0)):
                await self._send(self.connection.send_mouse(button=button, xPos=x, yPos=y, is_pressed=False, steps=rotation))
            return
        if action.coordinate is None:
            raise ValueError("mouse action requires a coordinate")
        x, y = denormalize_coordinate(action.coordinate, self.width, self.height)
        if action.kind is ActionKind.LEFT_CLICK:
            await self._click(x, y, "left")
        elif action.kind is ActionKind.RIGHT_CLICK:
            await self._click(x, y, "right")
        elif action.kind is ActionKind.DOUBLE_CLICK:
            await self._click(x, y, "left")
            await asyncio.sleep(0.1)
            await self._click(x, y, "left")
        else:
            raise ValueError(f"unsupported action: {action.kind.value}")

    async def _click(self, x: int, y: int, button: str) -> None:
        assert self.connection is not None and self._mouse_button is not None
        button_value = {
            "left": self._mouse_button.MOUSEBUTTON_LEFT,
            "right": self._mouse_button.MOUSEBUTTON_RIGHT,
        }[button]
        failed = False
        try:
            await self._send(self.connection.send_mouse(button=button_value, xPos=x, yPos=y, is_pressed=True))
            await asyncio.sleep(0.05)
        except BaseException:
            failed = True
            raise
        finally:
            try:
                await self._send(self.connection.send_mouse(button=button_value, xPos=x, yPos=y, is_pressed=False))
            except Exception:
                if not failed:
                    raise

    @staticmethod
    async def _send(operation) -> None:
        result = await operation
        if isinstance(result, tuple) and len(result) == 2 and result[1] is not None:
            raise RuntimeError("RDP input failed") from result[1]

    async def _type_text(self, text: str) -> None:
        assert self.connection is not None
        for char in text:
            failed = False
            try:
                await self._send(self.connection.send_key_char(char, True))
            except BaseException:
                failed = True
                raise
            finally:
                try:
                    await self._send(self.connection.send_key_char(char, False))
                except Exception:
                    if not failed:
                        raise
            await asyncio.sleep(0.03)

    async def _press_key(self, key: str) -> None:
        assert self.connection is not None
        parts = [part.strip().lower() for part in key.split("+") if part.strip()]
        if not parts:
            raise ValueError("key cannot be empty")
        modifiers = {"ctrl": (0x1D, False), "shift": (0x2A, False), "alt": (0x38, False), "win": (0x5B, True)}
        special = {
            "enter": (0x1C, False), "tab": (0x0F, False), "escape": (0x01, False),
            "backspace": (0x0E, False), "space": (0x39, False), "delete": (0x53, True),
            "left": (0x4B, True), "up": (0x48, True), "right": (0x4D, True), "down": (0x50, True),
            "home": (0x47, True), "end": (0x4F, True), "pageup": (0x49, True), "pagedown": (0x51, True),
        }
        letters = {
            "a": 0x1E, "b": 0x30, "c": 0x2E, "d": 0x20, "e": 0x12, "f": 0x21,
            "g": 0x22, "h": 0x23, "i": 0x17, "j": 0x24, "k": 0x25, "l": 0x26,
            "m": 0x32, "n": 0x31, "o": 0x18, "p": 0x19, "q": 0x10, "r": 0x13,
            "s": 0x1F, "t": 0x14, "u": 0x16, "v": 0x2F, "w": 0x11, "x": 0x2D,
            "y": 0x15, "z": 0x2C,
        }
        for modifier in parts[:-1]:
            if modifier not in modifiers:
                raise ValueError(f"unsupported modifier: {modifier}")
        main = parts[-1]
        if main in special:
            scan = special[main]
        elif main in letters:
            scan = (letters[main], False)
        else:
            raise ValueError(f"unsupported key: {main}")
        held: list[tuple[int, bool]] = []
        failed = False
        try:
            for modifier in parts[:-1]:
                modifier_scan = modifiers[modifier]
                held.append(modifier_scan)
                await self._send(self.connection.send_key_scancode(modifier_scan[0], True, modifier_scan[1]))
            held.append(scan)
            await self._send(self.connection.send_key_scancode(scan[0], True, scan[1]))
        except BaseException:
            failed = True
            raise
        finally:
            release_error = None
            for held_scan in reversed(held):
                try:
                    await self._send(self.connection.send_key_scancode(held_scan[0], False, held_scan[1]))
                except Exception as exc:
                    release_error = release_error or exc
            if release_error is not None and not failed:
                raise release_error
