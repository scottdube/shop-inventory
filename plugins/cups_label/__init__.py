"""CUPS Label — print InvenTree labels through the local CUPS queue.

Why this exists instead of the Brother plugin: the QL-810W's brother_ql raster
path does not work on this unit. It accepts every job on port 9100, prints
nothing, latches a red error, and has never once answered a status request --
not in P-touch Template emulation, not after switching Command Mode to Raster,
not with stock brother_ql CLI defaults against a freshly cleared printer.

The same printer's AirPrint/IPP stack is healthy: it reports idle with no error
reasons, correctly identifies its own media as 62mm continuous, and prints
correctly through CUPS driverlessly (IPP Everywhere, no Brother driver). So we
hand CUPS the PDF InvenTree already renders and let it do the rasterising.

Deliberately shells out to `lp` rather than using pycups: no build-time CUPS
headers, no new dependency, and the command is the one already verified by hand
against this queue.
"""

import os
import shutil
import subprocess
import tempfile

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from plugin import InvenTreePlugin
from plugin.mixins import LabelPrintingMixin, SettingsMixin

# The server runs under launchd, whose PATH is not a login shell's. lp lives in
# /usr/bin, but resolving it explicitly means a PATH change never turns printing
# into a confusing "no such file" at print time.
SEARCH_PATH = '/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin'


class CupsLabelPlugin(SettingsMixin, LabelPrintingMixin, InvenTreePlugin):
    """Send rendered label PDFs to a CUPS print queue."""

    NAME = 'CupsLabel'
    SLUG = 'cupslabel'
    TITLE = _('CUPS Label Printer')
    DESCRIPTION = _('Print labels via a local CUPS queue (lp)')
    VERSION = '0.1.0'
    AUTHOR = 'shop-inventory'

    # Print synchronously so a failure surfaces as an error in the UI rather
    # than a job that silently disappears into a worker.
    BLOCKING_PRINT = True

    SETTINGS = {
        'QUEUE': {
            'name': _('Queue name'),
            'description': _('CUPS destination, as shown by `lpstat -p`'),
            'default': 'QL810W',
        },
        'SET_PAGE_SIZE': {
            'name': _('Send page size'),
            'description': _(
                'Pass the label template size to CUPS as '
                'PageSize=Custom.WxHmm. Turn off to use the queue default.'
            ),
            'validator': bool,
            'default': True,
        },
        'EXTRA_OPTIONS': {
            'name': _('Extra lp options'),
            'description': _(
                'Space-separated, each applied with -o. '
                'e.g. "MediaType=Roll CutMedia=EndOfPage"'
            ),
            'default': '',
        },
    }

    def _lp(self):
        """Absolute path to lp, or None if it cannot be found."""
        return shutil.which('lp', path=SEARCH_PATH) or shutil.which('lp')

    def print_label(self, **kwargs):
        """Write the rendered PDF to a temp file and hand it to lp.

        kwargs of interest: pdf_data (bytes), width and height (mm, floats
        from the label template), filename (used as the job title so the queue
        is readable in lpstat).
        """
        pdf_data = kwargs.get('pdf_data')
        if not pdf_data:
            raise ValidationError(_('No PDF data was supplied to print'))

        lp = self._lp()
        if not lp:
            raise ValidationError(
                _('The `lp` command was not found on the server')
            )

        queue = (self.get_setting('QUEUE') or '').strip()
        if not queue:
            raise ValidationError(_('No CUPS queue name is configured'))

        cmd = [lp, '-d', queue]

        title = kwargs.get('filename') or 'inventree-label'
        cmd += ['-t', str(title)[:120]]

        # The template's own dimensions are authoritative. Without this CUPS
        # falls back to the queue's default page size -- which on this printer
        # is a die-cut size unrelated to the roll loaded, and the label comes
        # out scaled down on an overlong strip.
        if self.get_setting('SET_PAGE_SIZE'):
            w, h = kwargs.get('width'), kwargs.get('height')
            try:
                w, h = float(w), float(h)
            except (TypeError, ValueError):
                w = h = 0
            if w > 0 and h > 0:
                cmd += ['-o', f'PageSize=Custom.{w:g}x{h:g}mm',
                        '-o', 'print-scaling=none']

        for opt in (self.get_setting('EXTRA_OPTIONS') or '').split():
            cmd += ['-o', opt]

        tmp = None
        try:
            with tempfile.NamedTemporaryFile(
                    suffix='.pdf', delete=False) as fh:
                fh.write(pdf_data)
                tmp = fh.name
            cmd.append(tmp)

            res = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
                env=dict(os.environ, PATH=SEARCH_PATH))

            if res.returncode != 0:
                msg = (res.stderr or res.stdout or '').strip()
                raise ValidationError(
                    _('lp failed ({code}): {msg}').format(
                        code=res.returncode, msg=msg[:300] or 'no output')
                )
            return res.stdout.strip()

        except subprocess.TimeoutExpired:
            raise ValidationError(
                _('Timed out waiting for lp to accept the job')
            )
        finally:
            if tmp:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
