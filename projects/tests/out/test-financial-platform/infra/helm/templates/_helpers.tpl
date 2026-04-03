{/* Common labels */}
{{- define "financial-platform.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
nikame.project: financial-platform
{{- end }}
