try:
    from plone.restapi.interfaces import IJSONSummarySerializerMetadata
except ImportError:
    from zope.interface import Interface

    class IJSONSummarySerializerMetadata(Interface):
        """Fallback for older plone.restapi without this interface."""


from zope.interface import implementer


@implementer(IJSONSummarySerializerMetadata)
class JSONSummarySerializerMetadata:
    """Additional metadata to be exposed on listings."""

    def default_metadata_fields(self):
        return {"image_field", "image_scales", "effective", "Subject"}
