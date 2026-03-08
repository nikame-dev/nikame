{/* Common labels */}
{{- define "my-app----[b.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
nikame.project: my-app----[b
{{- end }}
