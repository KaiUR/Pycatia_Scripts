# Script Templates

Starting points for writing new Pycatia Scripts. Copy the template that best matches your use case, rename it using `Snake_Case_Descriptive_Name.py`, and follow the `EDIT:` and `# TODO:` markers.

## Choosing a Template

| Template | Document | GUI | Saves settings | Progress bar |
|---|---|---|---|---|
| `any_document_basic.py` | Any | No | No | No |
| `any_document_dialog.py` | Any | Yes | No | No |
| `part_document_basic.py` | CATPart | No | No | No |
| `part_document_dialog.py` | CATPart | Yes | No | No |
| `part_document_dialog_persistence.py` | CATPart | Yes | Yes | No |
| `part_document_dialog_persistence_progress.py` | CATPart | Yes | Yes | Yes |
| `process_document_basic.py` | CATProcess | No | No | No |
| `process_document_dialog.py` | CATProcess | Yes | No | No |
| `process_document_dialog_persistence.py` | CATProcess | Yes | Yes | No |
| `product_document_basic.py` | CATProduct | No | No | No |

See the [Writing Scripts](https://github.com/KaiUR/Pycatia_Scripts/wiki/Writing-Scripts) wiki page for full guidance including the persistent data pattern and contribution guidelines.
