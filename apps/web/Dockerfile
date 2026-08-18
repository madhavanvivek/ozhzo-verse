FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json turbo.json tsconfig.base.json ./
COPY packages/ ./packages/
COPY apps/web/ ./apps/web/

ARG NEXT_PUBLIC_API_URL=https://ozhzo-api.onrender.com/api/v1
ARG NEXT_PUBLIC_API_BASE_URL=https://ozhzo-api.onrender.com/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL

RUN npm install -g turbo
RUN npm install
RUN turbo run build --filter=@ozhzo/web

FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder --chown=nextjs:nodejs /app/apps/web/public ./apps/web/public

USER nextjs

EXPOSE 10000

CMD ["sh", "-c", "HOSTNAME=0.0.0.0 PORT=${PORT:-10000} node apps/web/server.js"]
