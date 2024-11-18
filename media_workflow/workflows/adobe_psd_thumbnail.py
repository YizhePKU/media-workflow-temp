from temporalio import activity, workflow


@workflow.defn(name="adobe-psd-thumbnail")
class ImageThumbnail:
    pass
