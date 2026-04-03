{/* Common labels */}
{{- define "microservices-fleet.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
nikame.project: microservices-fleet
{{- end }}
