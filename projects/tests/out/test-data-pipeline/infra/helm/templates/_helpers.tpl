{/* Common labels */}
{{- define "data-pipeline.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
nikame.project: data-pipeline
{{- end }}
