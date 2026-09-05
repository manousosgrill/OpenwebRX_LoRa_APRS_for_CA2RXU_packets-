from owrx.toolbox import TextParser
from owrx.reporting import ReportingEngine
from owrx.aprs import AprsParser, thirdpartyeRegex

import base64
import json
import logging

logger = logging.getLogger(__name__)


class LoraParser(TextParser):
    def __init__(self, service: bool = False):
        super().__init__(filePrefix="LORA", service=service)
        self.aprsParser = AprsParser()

    def setDialFrequency(self, frequency: int) -> None:
        super().setDialFrequency(frequency)
        self.aprsParser.setDialFrequency(frequency)

    def parse(self, msg: bytes):
        try:
            out = json.loads(msg)
        except Exception:
            return msg.decode("utf-8") + "\n"

        out["mode"] = "LORA"

        if self.frequency:
            out["freq"] = self.frequency

        if "payload" in out:
            try:
                payload = self.parsePayload(
                    out,
                    base64.b64decode(out["payload"])
                )

                if payload:
                    return payload

            except Exception as e:
                logger.error(
                    "Exception parsing LoRa payload: %s",
                    str(e)
                )

        ReportingEngine.getSharedInstance().spot(out)

        return out

    # Parse LoRa payload by type
    def parsePayload(self, out, data: bytes):
        if (
            len(data) > 3
            and data[0] == 0x3C
            and data[1] == 0xFF
            and data[2] == 0x01
        ):
            return self.parseAprs(out, data[3:])

        return None

    # Parse LoRa APRS payload
    def parseAprs(self, out, data: bytes):
        logger.debug(
            "LORA APRS RAW HEX: %s",
            data.hex(" ")
        )

        logger.debug(
            "LORA APRS RAW REPR: %r",
            data
        )

        try:
            payload = data.decode("utf-8").strip()

        except UnicodeDecodeError as e:
            logger.error(
                "LORA APRS UTF8 ERROR: %s",
                e
            )

            logger.error(
                "LORA APRS BAD DATA HEX: %s",
                data.hex(" ")
            )

            # CA2RXU LoRa APRS packets may contain binary data
            # after the normal ASCII APRS payload.
            #
            # Keep only the ASCII portion before the binary data.

            ascii_end = 0

            while ascii_end < len(data) and data[ascii_end] < 128:
                ascii_end += 1

            payload = data[:ascii_end].decode(
                "ascii",
                errors="strict"
            ).strip()

            logger.debug(
                "LORA APRS ASCII PAYLOAD: %r",
                payload
            )

        logger.debug(
            "LORA APRS DECODED: %r",
            payload
        )

        matches = thirdpartyeRegex.match(payload)

        if not matches:
            logger.warning(
                "Couldn't parse LoRa APRS payload: %r",
                payload
            )
            return None

        source = matches.group(1).upper()
        path = matches.group(2).split(",")
        info = matches.group(6)

        if "\x00" in info:
            info = info.split("\x00", 1)[0]

        logger.debug(
            "LORA APRS PARSED source=%r destination=%r "
            "path=%r info=%r",
            source,
            path[0] if path else "",
            path[1:] if len(path) > 1 else [],
            info
        )

        return self.aprsParser.process({
            "source": source,
            "destination": path[0] if path else "",
            "path": path[1:] if len(path) > 1 else [],
            "data": info.encode("utf-8"),
            "raw": data.hex().upper(),
        })
