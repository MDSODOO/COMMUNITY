import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import PurePosixPath


def _normalise_name(filename):
    stem = PurePosixPath(filename or '').stem.lower()
    return ''.join(char for char in stem if char.isalnum())


def _normalise_token(value):
    value = (value or '').lower()
    return ''.join(char for char in value if char.isalnum())


def _is_ignored_zip_entry(filename):
    path = PurePosixPath(filename or '')
    parts = [part.lower() for part in path.parts]
    name = path.name.lower()
    return (
        '__macosx' in parts
        or name.startswith('._')
        or name in {'.ds_store', 'thumbs.db'}
    )


def _looks_like_pdf(data):
    return b'%PDF' in (data or b'')[:1024]


@dataclass
class XmlPdfPair:
    xml_filename: str
    xml_bytes: bytes
    pdf_filename: str | None
    pdf_bytes: bytes | None
    cfdi_doc: object


@dataclass
class ZipContents:
    xml_files: list[tuple[str, bytes]] = field(default_factory=list)
    pdf_files: list[tuple[str, bytes]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def pair_xml_pdf(self, cfdi_docs):
        pairs = []
        used_pdf_indexes = set()

        for index, (xml_filename, xml_bytes) in enumerate(self.xml_files):
            doc = cfdi_docs[index] if index < len(cfdi_docs) else None
            pdf_index = self._match_pdf_by_name(xml_filename, used_pdf_indexes)
            if pdf_index is None and doc:
                pdf_index = self._match_pdf_by_folio(doc, used_pdf_indexes)
            if pdf_index is None and len(self.xml_files) == 1 and len(self.pdf_files) == 1:
                pdf_index = 0

            if pdf_index is None:
                pairs.append(XmlPdfPair(
                    xml_filename=xml_filename,
                    xml_bytes=xml_bytes,
                    pdf_filename=None,
                    pdf_bytes=None,
                    cfdi_doc=doc,
                ))
                continue

            used_pdf_indexes.add(pdf_index)
            pdf_filename, pdf_bytes = self.pdf_files[pdf_index]
            pairs.append(XmlPdfPair(
                xml_filename=xml_filename,
                xml_bytes=xml_bytes,
                pdf_filename=pdf_filename,
                pdf_bytes=pdf_bytes,
                cfdi_doc=doc,
            ))

        return pairs

    def _match_pdf_by_name(self, xml_filename, used_pdf_indexes):
        xml_key = _normalise_name(xml_filename)
        for index, (pdf_filename, _pdf_bytes) in enumerate(self.pdf_files):
            if index in used_pdf_indexes:
                continue
            if _normalise_name(pdf_filename) == xml_key:
                return index
        return None

    def _match_pdf_by_folio(self, doc, used_pdf_indexes):
        folios = [
            _normalise_token(getattr(doc, 'folio_completo', None)),
            _normalise_token(getattr(doc, 'folio', None)),
        ]
        folios = [folio for folio in folios if folio]
        if not folios:
            return None
        for index, (pdf_filename, _pdf_bytes) in enumerate(self.pdf_files):
            if index in used_pdf_indexes:
                continue
            pdf_key = _normalise_name(pdf_filename)
            if any(folio in pdf_key for folio in folios):
                return index
        return None


class ZipExtractor:
    def extract(self, zip_bytes):
        contents = ZipContents()
        try:
            archive = zipfile.ZipFile(BytesIO(zip_bytes))
        except zipfile.BadZipFile:
            contents.errors.append('El archivo ZIP no es valido.')
            return contents

        for info in archive.infolist():
            if info.is_dir():
                continue
            filename = info.filename
            if _is_ignored_zip_entry(filename):
                continue
            lower = filename.lower()
            try:
                data = archive.read(info)
            except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                contents.errors.append(f'No se pudo leer {filename}: {exc}')
                continue

            if lower.endswith('.xml'):
                contents.xml_files.append((filename, data))
            elif lower.endswith('.pdf'):
                if not _looks_like_pdf(data):
                    contents.errors.append(f'Se omitio {filename}: no parece un PDF valido.')
                    continue
                contents.pdf_files.append((filename, data))

        if not contents.xml_files:
            contents.errors.append('El ZIP no contiene archivos XML CFDI.')

        contents.xml_files.sort(key=lambda item: item[0].lower())
        contents.pdf_files.sort(key=lambda item: item[0].lower())
        return contents
