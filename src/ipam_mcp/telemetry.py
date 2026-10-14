import logging
import os
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


class ToolSpanProcessor(BatchSpanProcessor):
    def on_end(self, span) -> None:
        if span.name.startswith("mcp.tool.") and span.attributes and span.attributes.get("openinference.span.kind") == "TOOL":
            super().on_end(ReadableSpan(name=span.name, context=span.context, resource=span.resource, attributes=span.attributes, events=span.events, links=span.links, kind=span.kind, instrumentation_scope=span.instrumentation_scope, status=span.status, start_time=span.start_time, end_time=span.end_time))


def configure_telemetry() -> None:
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    otlp_headers = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
    project_name = os.getenv("OTEL_SERVICE_NAME", "enterprise-ipam-mcp")
    processors = []

    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint, headers=otlp_headers)
        processors.append(ToolSpanProcessor(exporter))

    resource = Resource.create({"service.name": project_name, "openinference.project.name": project_name})
    if connection_string:
        configure_azure_monitor(connection_string=connection_string, logger_name="ipam_mcp.audit", resource=resource, span_processors=processors)
    elif processors:
        provider = TracerProvider(resource=resource)
        for processor in processors:
            provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
