"""be_civic_dossier — Be Civic dossier renderer package.

The renderer is split across two streams:

* **Stream A** owns the Dossier container plus the six layout classes
  (IdCard / FullPageCert / MultiPageDoc / FeeReceipt / FilledForm /
  Placeholder), the watermark, cover, checklist, officer-notes, and
  metadata helpers.
* **Stream B** owns the HTML templates at
  ``../../skills/bc-dossier-compilation/templates/`` and the codegen
  module (``codegen.py``) that the agent uses to write ``render.py`` into
  the user's project folder.

This ``__init__`` re-exports the public surface from both streams. When the
two streams merge to dev, this file is a strict subset of Stream B's
defensively-typed version — Stream B's file wins the merge (it imports
the same renderer classes the same way) and gains the codegen exports.

Public surface used by user-side ``render.py``::

    from be_civic_dossier import (
        Dossier, IdCard, FullPageCert, MultiPageDoc,
        FeeReceipt, FilledForm, Placeholder,
    )
"""

from __future__ import annotations

# Stream A renderer classes.
from .renderer import Dossier
from .layouts import (
    FeeReceipt,
    FilledForm,
    FullPageCert,
    IdCard,
    MultiPageDoc,
    Placeholder,
)

__all__ = (
    "Dossier",
    "IdCard",
    "FullPageCert",
    "MultiPageDoc",
    "FeeReceipt",
    "FilledForm",
    "Placeholder",
)
